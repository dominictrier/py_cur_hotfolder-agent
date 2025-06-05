from hotfolder.config import load_global_config, get_effective_config, generate_example_config_dict
from hotfolder.logger import get_hotfolder_logger, get_hotfolder_debug_logger
from hotfolder.utils import is_folder_stable, normalize_path, is_image_file
from hotfolder.mover import move_hotfolder_contents, write_metadata
import os
import time
from pathlib import Path
import threading
from datetime import datetime, timedelta
import sys
import shutil
from hotfolder.state_db import HotfolderStateDB
import yaml
import unicodedata

class HotfolderWatcher:
    def __init__(self):
        self.global_config = load_global_config()
        self.debug = self.global_config.get('debug', True)
        # Validate config
        try:
            from hotfolder.config import validate_config
            validate_config(self.global_config)
        except Exception as e:
            logger = get_hotfolder_logger("global")
            logger.error(f"Invalid config: {e}")
            while True:
                time.sleep(3600)
        if self.debug:
            ordered_config = generate_example_config_dict(include_hotfolders=True, example_config=self.global_config)
            print(f"[DEBUG][hotfolder: global] Raw global config loaded:\n{yaml.safe_dump(dict(ordered_config), indent=2, sort_keys=False)}")
        # Normalize all hotfolder root paths to fix escaped spaces
        self.hotfolder_roots = [normalize_path(hf) for hf in self.global_config.get("hotfolders", [])]
        if self.debug:
            self._debug_print('global', f"Normalized hotfolder roots list: {self.hotfolder_roots}", debug_enabled=self.debug)
        self.running = False
        self.threads = {}  # {subfolder_path: thread}
        self.last_status = {}
        self.lock = threading.Lock()

    def run(self):
        self.running = True
        if self.debug:
            self._debug_print('global', "Starting dynamic hotfolder watcher...", debug_enabled=self.debug)
        # --- Heartbeat: only support nested config ---
        heartbeat_enabled = False
        if "heartbeat" in self.global_config and isinstance(self.global_config["heartbeat"], dict):
            heartbeat_enabled = self.global_config["heartbeat"].get("heartbeat_enabled", False)
        # Place heartbeat in project root
        project_root = Path(__file__).parent.parent.resolve()
        heartbeat_dir = project_root / "heartbeat"
        heartbeat_dir.mkdir(exist_ok=True)
        heartbeat_file = heartbeat_dir / "heartbeat.txt"
        try:
            while self.running:
                try:
                    self.scan_and_update_hotfolders()
                except Exception as e:
                    logger = get_hotfolder_logger("global")
                    logger.error(f"Unhandled error in scan loop: {e}")
                # Write heartbeat if enabled
                if heartbeat_enabled:
                    with open(heartbeat_file, "w") as f:
                        f.write(datetime.now().isoformat())
                time.sleep(self.global_config.get("scan_interval", 10))
        except KeyboardInterrupt:
            self.running = False
            print("Shutting down watcher...")

    def scan_and_update_hotfolders(self):
        current_hotfolders = set()
        hotfolder_pairs = {}  # {in_subfolder: out_subfolder}
        for root in self.hotfolder_roots:
            root_path = Path(root).resolve()
            if not root_path.exists():
                if self.debug:
                    self._debug_print(root, f"[WARNING] Hotfolder root does not exist: {root_path}", debug_enabled=self.debug)
                continue
            for subfolder in root_path.iterdir():
                if subfolder.is_dir() and not subfolder.name.startswith('.') and not subfolder.name.endswith('_out'):
                    current_hotfolders.add(str(subfolder))
                    out_subfolder = root_path / f"{subfolder.name}_out"
                    hotfolder_pairs[str(subfolder)] = out_subfolder
                    # Ensure OUT folder exists immediately
                    out_subfolder.mkdir(parents=True, exist_ok=True)
        # Start threads for new hotfolders
        with self.lock:
            for folder in current_hotfolders:
                if folder not in self.threads:
                    if self.debug:
                        self._debug_print(folder, "Starting watcher for new hotfolder.", debug_enabled=self.debug)
                    out_subfolder = hotfolder_pairs[folder]
                    t = threading.Thread(target=self.watch_hotfolder, args=(folder, out_subfolder), daemon=True)
                    t.start()
                    self.threads[folder] = t
            # Remove threads for hotfolders that no longer exist
            removed = [f for f in self.threads if f not in current_hotfolders]
            for folder in removed:
                if self.debug:
                    self._debug_print(folder, "Hotfolder removed or no longer exists.", debug_enabled=self.debug)
                del self.threads[folder]
        if self.debug:
            self._debug_print('global', f"Currently watched hotfolders: {list(self.threads.keys())}", debug_enabled=self.debug)

    def watch_hotfolder(self, folder_path, out_subfolder):
        folder = Path(folder_path).resolve()
        config = get_effective_config(folder, self.global_config)
        # Determine debug mode for this hotfolder
        hotfolder_debug = config.get("debug", self.debug)
        debug_enabled = hotfolder_debug
        if debug_enabled:
            ordered_config = generate_example_config_dict(include_hotfolders=False, example_config=config)
            folder_name = folder.name if hasattr(folder, 'name') else str(folder)
            print(f"[DEBUG][hotfolder: {folder_name}] Effective config loaded (per-hotfolder):\n{yaml.safe_dump(dict(ordered_config), indent=2, sort_keys=False)}")
        out_subfolder.mkdir(parents=True, exist_ok=True)
        while self.running:
            try:
                self.handle_hotfolder(folder, out_subfolder, hotfolder_debug)
            except FileNotFoundError as e:
                # Only suppress/log as debug if the missing path is the folder itself or a direct subfolder (job folder)
                missing_path = Path(getattr(e, 'filename', ''))
                if missing_path == folder or missing_path.parent == folder:
                    if hotfolder_debug:
                        self._debug_print(folder, f"[SKIP] Folder or job folder not found during scan (likely just moved): {e}", debug_enabled=hotfolder_debug)
                    # Do not log as error
                else:
                    logger = get_hotfolder_logger(folder)
                    logger.error(f"Unhandled error in hotfolder thread: {e}")
                    if hotfolder_debug:
                        self._debug_print(folder, f"[ERROR] Unhandled error in hotfolder thread: {e}", debug_enabled=hotfolder_debug)
            except Exception as e:
                logger = get_hotfolder_logger(folder)
                logger.error(f"Unhandled error in hotfolder thread: {e}")
                if hotfolder_debug:
                    self._debug_print(folder, f"[ERROR] Unhandled error in hotfolder thread: {e}", debug_enabled=hotfolder_debug)
            time.sleep(config.get("scan_interval", 10))

    def handle_hotfolder(self, folder, out_folder, hotfolder_debug=None):
        # Remove old state files if present
        if not folder.exists():
            config = get_effective_config(folder, self.global_config)
            debug_enabled = config.get("debug", self.debug)
            if debug_enabled:
                self._debug_print(folder, f"[SKIP] Folder {folder} no longer exists, skipping.", debug_enabled=debug_enabled)
            return

        # Use SQLite state DB
        state_db = HotfolderStateDB(folder)
        
        # Get current files and folders
        current_items = {str(f.relative_to(folder)) for f in folder.iterdir() if not f.name.startswith('.')}
        
        # Clean up seen and processed entries for removed items
        seen = state_db.get_seen()
        processed = state_db.get_processed()
        
        # Clean up seen state for any removed items
        for seen_path in list(seen.keys()):
            # Skip if item still exists
            if seen_path in current_items:
                continue
            # Item was removed (by workflow, retention, or user) - clean up its state
            state_db.remove_seen(seen_path)
            if debug_enabled:
                self._debug_print(folder, f"[CLEANUP] Removed seen state for removed item: {seen_path}", debug_enabled=debug_enabled)
        
        # Clean up processed state for any removed items
        for processed_path in list(processed.keys()):
            # Skip if item still exists
            if processed_path in current_items:
                continue
            # Item was removed (by workflow, retention, or user) - clean up its state
            state_db.remove_processed(processed_path)
            if debug_enabled:
                self._debug_print(folder, f"[CLEANUP] Removed processed state for removed item: {processed_path}", debug_enabled=debug_enabled)

        # Deferred deletion: clean up any job folders marked for deletion
        ready_for_deletion = state_db.get_ready_for_deletion_jobs()
        for job_name in ready_for_deletion:
            job_folder = folder / job_name
            if job_folder.exists() and job_folder.is_dir() and not any(job_folder.iterdir()):
                try:
                    job_folder.rmdir()
                    # Clean up state for this job folder and all its files
                    state_db.remove_seen_prefix(job_name)
                    state_db.remove_processed_prefix(job_name)
                    config = get_effective_config(folder, self.global_config)
                    debug_enabled = config.get("debug", self.debug)
                    logger = get_hotfolder_logger(folder, retention_days=config.get("log_retention", 7))
                    if debug_enabled:
                        self._debug_print(folder, f"[CLEANUP] Deleted marked job folder: {job_folder}", debug_enabled=debug_enabled)
                    self.log_action(logger, folder, "CLEANUP", f"Deleted marked job folder: {job_folder}")
                except Exception as e:
                    if debug_enabled:
                        self._debug_print(folder, f"[CLEANUP] Failed to delete marked job folder {job_folder}: {e}", debug_enabled=debug_enabled)

        # Determine debug mode for this hotfolder
        if hotfolder_debug is None:
            config = get_effective_config(folder, self.global_config)
            hotfolder_debug = config.get("debug", self.debug)
        else:
            config = get_effective_config(folder, self.global_config)
        debug_enabled = hotfolder_debug
        # Never execute or import code from the hotfolder
        for f in folder.iterdir():
            if f.suffix in {'.py', '.pyc', '.pyo', '.sh', '.bash', '.zsh', '.pl', '.rb', '.php', '.js', '.exe', '.dll', '.so', '.dylib'}:
                continue  # Just skip, never execute or import
        logger = get_hotfolder_logger(folder, retention_days=config.get("log_retention", 7))
        resting_time = config.get("resting_time", 300)
        dissolve_folders = config.get("dissolve_folders", False)
        metadata = config.get("metadata", False)
        metadata_field = config.get("metadata_field", "headline")
        cleanup_enabled = config.get("cleanup", True)
        keep_copy = self.validate_bool(config.get("keep_copy", False), "keep_copy", False)
        cleanup_time = config.get("cleanup_time", 1440)
        ignore_updates = self.validate_bool(config.get("ignore_updates", False), "ignore_updates", False)
        update_mtime = config.get("update_mtime", True)
        ds_store = config.get("ds_store", True)
        thumbs_db = config.get("thumbs_db", True)
        inject_folder_name = config.get("inject_folder_name", False)
        now = time.time()
        # Use DB for state
        processed = state_db.get_processed()
        seen = state_db.get_seen()
        files = [f for f in folder.iterdir() if not f.name.startswith('.')]
        changed = False
        for idx, f in enumerate(files):
            if not f.exists():
                continue
            rel = str(f.relative_to(folder))
            f_path = folder / rel
            # 1. Add to seen if new
            if rel not in seen:
                mtime = f_path.stat().st_mtime
                state_db.set_seen(rel, now, mtime)
                changed = True
                if debug_enabled:
                    self._debug_print(folder, f"[DB] Added to seen: {rel}", debug_enabled=debug_enabled)
                if idx > 0:
                    logger.info("")
                self.log_action(logger, folder, "ARRIVED", f"New file/folder: {rel}")
                if f_path.is_dir():
                    for subfile in f_path.rglob('*'):
                        if subfile.is_file():
                            subrel = str(subfile.relative_to(folder))
                            submtime = subfile.stat().st_mtime
                            state_db.set_seen(subrel, now, submtime)
                            if debug_enabled:
                                self._debug_print(folder, f"[DB] Added to seen: {subrel}", debug_enabled=debug_enabled)
                            logger.info(f"    [CONTAINS] {subrel}")
            # --- Resting time fix: reset seen_time if any file changes ---
            if f_path.is_dir():
                # Recursively check all files and subfolders
                last_seen = seen[rel]['seen_time'] if rel in seen else now
                latest_mtime = last_seen
                file_set = set()
                file_mtimes = {}
                for subfile in f_path.rglob('*'):
                    if subfile.is_file():
                        subrel = unicodedata.normalize('NFC', str(subfile.relative_to(folder)))
                        file_set.add(subrel)
                        mtime = subfile.stat().st_mtime
                        file_mtimes[subrel] = mtime
                        # Add new files to seen
                        if subrel not in seen:
                            state_db.set_seen(subrel, now, mtime)
                            changed = True
                # Normalize seen files for this job
                seen_files_for_job = {unicodedata.normalize('NFC', k) for k in seen if k.startswith(rel + '/')}
                # Extra debug: log normalized file sets
                if debug_enabled:
                    self._debug_print(folder, f"[DEBUG] repr(file_set): {repr(sorted(file_set))}", debug_enabled=debug_enabled)
                    self._debug_print(folder, f"[DEBUG] repr(seen_files_for_job): {repr(sorted(seen_files_for_job))}", debug_enabled=debug_enabled)
                # Compare file_set to seen files for this job
                files_added = file_set - seen_files_for_job
                files_removed = seen_files_for_job - file_set
                mtimes_changed = set()
                for fname in file_set & seen_files_for_job:
                    current_mtime = file_mtimes.get(fname)
                    seen_mtime = seen.get(fname, {}).get('mtime')
                    if seen_mtime is not None and current_mtime != seen_mtime:
                        mtimes_changed.add(fname)
                # Remove deleted files from seen (only for this job)
                deleted_from_seen = {k for k in seen if k.startswith(rel + '/') and k not in file_set}
                for subrel in deleted_from_seen:
                    state_db.remove_seen(subrel)
                    changed = True
                    if debug_enabled:
                        self._debug_print(folder, f"[DB] Removed from seen: {subrel}", debug_enabled=debug_enabled)
                # Reset seen_time if any file added, removed, or mtime changed
                if files_added or files_removed or mtimes_changed or deleted_from_seen:
                    state_db.set_seen(rel, now, f_path.stat().st_mtime)
                    changed = True
                    if debug_enabled:
                        file_set_str = ', '.join(sorted(file_set))
                        self._debug_print(folder, f"[RESTING] File set for {rel}: [{file_set_str}]", debug_enabled=debug_enabled)
                        if file_set:
                            mtimes_str = '; '.join([
                                f"{fname}:cur={file_mtimes.get(fname)},seen={seen.get(fname, {}).get('mtime')}"
                                for fname in sorted(file_set)
                            ])
                            self._debug_print(folder, f"[RESTING] File mtimes for {rel}: {mtimes_str}", debug_enabled=debug_enabled)
                        debug_msg = f"[RESTING] Reset seen_time for {rel} due to file change (mtime or file set)"
                        if files_added:
                            debug_msg += f" | Added: {sorted(files_added)}"
                        if files_removed:
                            debug_msg += f" | Removed: {sorted(files_removed)}"
                        if mtimes_changed:
                            debug_msg += f" | Modified: {sorted(mtimes_changed)}"
                        if deleted_from_seen:
                            debug_msg += f" | Deleted from seen: {sorted(deleted_from_seen)}"
                        self._debug_print(folder, debug_msg, debug_enabled=debug_enabled)
                # After moving/copying all files with dissolve_folders, if the job folder is deleted, return immediately
                if not f_path.exists():
                    config = get_effective_config(folder, self.global_config)
                    debug_enabled = config.get("debug", self.debug)
                    if debug_enabled:
                        self._debug_print(folder, f"[SKIP] Job folder {f_path} was deleted during processing, skipping further processing this scan.", debug_enabled=debug_enabled)
                    return
            elif f_path.is_file():
                mtime = f_path.stat().st_mtime
                if rel in seen:
                    prev_mtime = seen[rel]['mtime']
                    if mtime != prev_mtime:
                        if debug_enabled:
                            self._debug_print(folder, f"[RESTING] mtime changed for {rel}: old={prev_mtime}, new={mtime}", debug_enabled=debug_enabled)
                        state_db.set_seen(rel, now, mtime)
                        changed = True
                        self._debug_print(folder, f"[RESTING] Reset seen_time for {rel} due to mtime change", debug_enabled=debug_enabled)
            # 2. Check if stable
            seen_time = seen[rel]['seen_time'] if rel in seen else now
            stable = (now - seen_time) >= resting_time

            if stable:
                f_path = folder / rel
                if f_path.is_dir():
                    # Check if ALL files in the folder have rested
                    all_files_rested = True
                    for subfile in f_path.rglob('*'):
                        if subfile.is_file():
                            subrel = str(subfile.relative_to(folder))
                            if subrel in seen:
                                sub_seen_time = seen[subrel]['seen_time']
                                if (now - sub_seen_time) < resting_time:
                                    all_files_rested = False
                                    if debug_enabled:
                                        self._debug_print(folder, f"[RESTING] File {subrel} has not rested long enough: seen_time={sub_seen_time}, now={now}, delta={now - sub_seen_time:.1f}s (resting_time={resting_time}s)", debug_enabled=debug_enabled)
                                    break
                            else:
                                all_files_rested = False
                                if debug_enabled:
                                    self._debug_print(folder, f"[RESTING] File {subrel} not yet seen", debug_enabled=debug_enabled)
                                break
                    
                    if not all_files_rested:
                        if debug_enabled:
                            self._debug_print(folder, f"[RESTING] Not all files in {rel} have rested long enough", debug_enabled=debug_enabled)
                        continue

                    if keep_copy:
                        # Recursively process files in the job folder
                        job_files = [sf for sf in f_path.rglob('*') if sf.is_file()]
                        processed_entry = {k: v for k, v in processed.items() if k.startswith(rel + '/')}
                        processed_files = processed_entry
                        to_process = []
                        current_files = set()
                        for sf in job_files:
                            srel = str(sf.relative_to(folder))
                            smtime = sf.stat().st_mtime
                            current_files.add(srel)
                            pf = processed_files.get(srel, {})
                            if pf.get('mtime') != smtime:
                                to_process.append((sf, srel, smtime))
                        if to_process:
                            moved_count = 0
                            for sf, srel, smtime in to_process:
                                out_path = out_folder / srel
                                out_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(str(sf), str(out_path))
                                moved_count += 1
                                if debug_enabled:
                                    self._debug_print(folder, f"[PER-FILE] Copied {srel} to OUT (resting_time={resting_time}, stable={stable}).", debug_enabled=debug_enabled)
                            # Update processed entry
                            for _, srel, smtime in to_process:
                                # Ensure processed_time is set
                                state_db.set_processed(srel, now, smtime)
                                if debug_enabled:
                                    self._debug_print(folder, f"[DB] Added to processed: {srel}", debug_enabled=debug_enabled)
                            changed = True
                            self.log_action(logger, folder, "PROCESSED", f"Processed {rel}, moved_count={moved_count}")
                            if debug_enabled:
                                self._debug_print(folder, f"[PROCESSED] Processed {rel}, moved_count={moved_count}", debug_enabled=debug_enabled)
                        # Handle deletions: remove entries for files no longer present
                        removed_files = set(processed_files.keys()) - current_files
                        for srel in removed_files:
                            state_db.remove_processed(srel)
                            changed = True
                            self.log_action(logger, folder, "REMOVED", f"File removed from IN: {srel}")
                            if debug_enabled:
                                self._debug_print(folder, f"[DB] Removed from processed: {srel}", debug_enabled=debug_enabled)
                    elif keep_copy and f_path.is_file():
                        smtime = f_path.stat().st_mtime
                        pf = processed.get(rel, {})
                        if pf.get('mtime') != smtime:
                            out_path = out_folder / rel
                            out_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(f_path), str(out_path))
                            state_db.set_processed(rel, now, smtime)
                            changed = True
                            self.log_action(logger, folder, "PROCESSED", f"Processed {rel}, moved_count=1")
                            if debug_enabled:
                                self._debug_print(folder, f"[PROCESSED] Processed {rel}, moved_count=1", debug_enabled=debug_enabled)
                    elif not keep_copy:
                        # Move logic unchanged: move whole job after resting_time
                        if rel not in processed:
                            if debug_enabled:
                                self._debug_print(folder, f"[PROCESSING] {rel} is stable, moving now.", debug_enabled=debug_enabled)
                            moved_count, marked_for_deletion = move_hotfolder_contents(
                                folder, out_folder, dissolve_folders, metadata, metadata_field, logger, keep_copy, ignore_updates, update_mtime, ds_store, thumbs_db)
                            state_db.set_processed(rel, now, f_path.stat().st_mtime)
                            # Mark for deferred deletion if needed
                            if dissolve_folders and rel in marked_for_deletion:
                                state_db.mark_ready_for_deletion(rel)
                            changed = True
                            self.log_action(logger, folder, "PROCESSED", f"Processed {rel}, moved_count={moved_count}")
                            if debug_enabled:
                                self._debug_print(folder, f"[PROCESSED] Processed {rel}, moved_count={moved_count}", debug_enabled=debug_enabled)
                            # After moving, check if folder still exists
                            if not f_path.exists():
                                if debug_enabled:
                                    self._debug_print(folder, f"[INFO] Folder {f_path} was moved and no longer exists. Exiting processing loop.", debug_enabled=debug_enabled)
                                return
            # 4. Log status
            processed_time = processed.get(rel, {}).get("processed_time")
            age = (now - processed_time) if processed_time else None
            if debug_enabled:
                if f_path.is_dir():
                    # For debug output only: check processed times of files
                    processed_files = {k: v for k, v in processed.items() if k.startswith(rel + '/')}
                    if processed_files:
                        latest_processed = max(v.get('processed_time', 0) for v in processed_files.values())
                        self._debug_print(folder, f"Folder: {f}, seen_time: {seen_time}, stable: {stable}, processed_time: {latest_processed}, age: {(now - latest_processed) if latest_processed else 'N/A'} (from processed files)", debug_enabled=debug_enabled)
                    else:
                        # Check if the folder itself is processed
                        folder_processed = processed.get(rel, {}).get("processed_time")
                        if folder_processed:
                            self._debug_print(folder, f"Folder: {f}, seen_time: {seen_time}, stable: {stable}, processed_time: {folder_processed}, age: {(now - folder_processed) if folder_processed else 'N/A'} (folder processed)", debug_enabled=debug_enabled)
                        else:
                            self._debug_print(folder, f"Folder: {f}, seen_time: {seen_time}, stable: {stable}, processed_time: None, age: N/A (no processed files or folder)", debug_enabled=debug_enabled)
                else:
                    self._debug_print(folder, f"File: {f}, seen_time: {seen_time}, stable: {stable}, processed_time: {processed_time}, age: {age if age is not None else 'N/A'}", debug_enabled=debug_enabled)
            # After each file/folder, check if the parent folder still exists
            if not folder.exists():
                config = get_effective_config(folder, self.global_config)
                debug_enabled = config.get("debug", self.debug)
                if debug_enabled:
                    self._debug_print(folder, f"[SKIP] Folder {folder} was deleted during scan, aborting.", debug_enabled=debug_enabled)
                return
            # After resting, before move/dissolve, inject metadata if enabled
            if inject_folder_name and metadata_field and f_path.is_dir():
                folder_name = f_path.name
                for subfile in f_path.rglob('*'):
                    if subfile.is_file() and is_image_file(subfile):
                        if debug_enabled:
                            self._debug_print(folder, f"[METADATA] Attempting to write '{folder_name}' to field '{metadata_field}' in {subfile}", debug_enabled=debug_enabled)
                        write_metadata(str(subfile), metadata_field, folder_name, logger)
                        if debug_enabled:
                            self._debug_print(folder, f"[METADATA] Successfully wrote metadata for {subfile}. File has passed metadata process.", debug_enabled=debug_enabled)
            elif inject_folder_name and metadata_field and f_path.is_file() and is_image_file(f_path):
                folder_name = folder.name
                if debug_enabled:
                    self._debug_print(folder, f"[METADATA] Attempting to write '{folder_name}' to field '{metadata_field}' in {f_path}", debug_enabled=debug_enabled)
                write_metadata(str(f_path), metadata_field, folder_name, logger)
                if debug_enabled:
                    self._debug_print(folder, f"[METADATA] Successfully wrote metadata for {f_path}. File has passed metadata process.", debug_enabled=debug_enabled)
        # 5. Retention cleanup
        if cleanup_enabled and keep_copy and cleanup_time > 0:
            # Debug: show all processed entries and their processed_time
            if debug_enabled:
                debug_msg = f"[RETENTION] Processed entries for cleanup check (cleanup_time={cleanup_time} min):\n"
                for rel, entry in processed.items():
                    pt = entry.get("processed_time")
                    age = (now - pt) / 60 if pt else None
                    exists = (folder / rel).exists()
                    debug_msg += f"  {rel}: processed_time={pt}, age_min={age:.2f}, exists={exists}\n" if pt else f"  {rel}: processed_time=None, exists={exists}\n"
                self._debug_print(folder, debug_msg.rstrip(), debug_enabled=debug_enabled)
            
            # Clean up processed entries for files that no longer exist or are past retention
            for rel, entry in list(processed.items()):
                pt = entry.get("processed_time")
                abs_path = folder / rel
                file_exists = abs_path.exists()
                
                # Clean up if file doesn't exist OR if it's past retention time
                if not file_exists or (pt and (now - pt) / 60 > cleanup_time):
                    # If file exists and is past retention, delete it
                    if file_exists:
                        try:
                            abs_path.unlink()
                            if debug_enabled:
                                self._debug_print(folder, f"[RETENTION] Deleted {rel} from IN after {cleanup_time} minutes due to retention policy.", debug_enabled=debug_enabled)
                            self.log_action(logger, folder, "RETENTION", f"Deleted {rel} from IN after {cleanup_time} minutes due to retention policy.")
                        except Exception as e:
                            if debug_enabled:
                                self._debug_print(folder, f"[RETENTION] Failed to delete {rel}: {e}", debug_enabled=debug_enabled)
                    
                    # Always clean up DB entries for non-existent files or those past retention
                    state_db.remove_seen(rel)
                    state_db.remove_processed(rel)
                    if debug_enabled:
                        reason = "file no longer exists" if not file_exists else f"past retention time ({cleanup_time} min)"
                        self._debug_print(folder, f"[RETENTION] Cleaned up DB entries for {rel} because {reason}", debug_enabled=debug_enabled)

            # After deleting files, check if the job folder is empty and delete it if so
            for job_folder in folder.iterdir():
                if job_folder.is_dir():
                    # Only consider job folders, not .db/.log etc
                    if job_folder.name.startswith('.'):
                        continue
                    if not any(job_folder.iterdir()):
                        try:
                            job_folder.rmdir()
                            # Clean up state for this job folder and all its files
                            state_db.remove_seen_prefix(job_folder.name)
                            state_db.remove_processed_prefix(job_folder.name)
                            if debug_enabled:
                                self._debug_print(folder, f"[RETENTION] Deleted empty job folder {job_folder.name} after retention cleanup.", debug_enabled=debug_enabled)
                            self.log_action(logger, folder, "RETENTION", f"Deleted {job_folder.name} from IN after retention policy (folder was empty).")
                        except Exception as e:
                            if debug_enabled:
                                self._debug_print(folder, f"[RETENTION] Failed to delete job folder {job_folder.name}: {e}", debug_enabled=debug_enabled)
        # 6. Save state (no-op for DB)
        # Clean up processed/seen if empty (no-op for DB)

    def _debug_print(self, folder, message, debug_enabled=None):
        # folder: 'global' or hotfolder path
        global_debug = self.debug
        per_hotfolder_debug = False
        folder_name = folder if folder == 'global' else Path(folder).name
        if folder != 'global':
            # Get per-hotfolder debug setting
            config = get_effective_config(folder, self.global_config)
            per_hotfolder_debug = config.get('debug', global_debug)
        if folder == 'global':
            if global_debug:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                debug_msg = f"[DEBUG][{ts}][hotfolder: global] {message}"
                print(debug_msg)
                debug_logger = get_hotfolder_debug_logger('global')
                debug_logger.debug(message)
        else:
            if per_hotfolder_debug:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                debug_msg = f"[DEBUG][{ts}][hotfolder: {folder_name}] {message}"
                print(debug_msg)
                debug_logger = get_hotfolder_debug_logger(folder)
                debug_logger.debug(message)

    def log_action(self, logger, folder, action, details, level="info"):
        # Use only the folder name for per-hotfolder logs
        folder_str = str(folder)
        if folder_str != 'global':
            folder_str = Path(folder_str).name
        msg = f"[HOTFOLDER: {folder_str}] [{action}] {details}"
        if level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        else:
            logger.info(msg)

    def validate_bool(self, val, key, default):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            if val.lower() in ("true", "yes", "1"): return True
            if val.lower() in ("false", "no", "0"): return False
        self._debug_print('global', f"[WARNING] {key} is not a valid boolean: {val}. Using default {default}.", debug_enabled=self.debug)
        return default 