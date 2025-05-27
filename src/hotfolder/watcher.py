from hotfolder.config import load_global_config, get_effective_config
from hotfolder.logger import get_hotfolder_logger
from hotfolder.utils import is_folder_stable, normalize_path
from hotfolder.mover import move_hotfolder_contents, cleanup_processed_json, load_processed, load_seen, save_seen, save_processed
import os
import time
from pathlib import Path
import threading
from datetime import datetime, timedelta
import json
import sys
from hotfolder.heartbeat import write_heartbeat
import shutil

class HotfolderWatcher:
    def __init__(self):
        config_path = Path(__file__).parent.parent.parent / "config.json"
        if not config_path.exists():
            while True:
                time.sleep(3600)
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
            print(f"[DEBUG][hotfolder: global] Raw global config loaded:\n{json.dumps(self.global_config, indent=2)}")
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
        try:
            while self.running:
                try:
                    self.scan_and_update_hotfolders()
                except Exception as e:
                    logger = get_hotfolder_logger("global")
                    logger.error(f"Unhandled error in scan loop: {e}")
                write_heartbeat()
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
                # Remove OUT subfolder if empty
                in_folder = Path(folder)
                out_subfolder = in_folder.parent / f"{in_folder.name}_out"
                if out_subfolder.exists() and out_subfolder.is_dir():
                    try:
                        if not any(out_subfolder.iterdir()):
                            out_subfolder.rmdir()
                    except Exception:
                        pass
                del self.threads[folder]
        if self.debug:
            self._debug_print('global', f"Currently watched hotfolders: {list(self.threads.keys())}", debug_enabled=self.debug)

    def watch_hotfolder(self, folder_path, out_subfolder):
        folder = Path(folder_path).resolve()
        config = get_effective_config(folder, self.global_config)
        # Determine debug mode for this hotfolder
        hotfolder_debug = config.get("debug", self.debug)
        if self.debug or hotfolder_debug:
            print(f"[DEBUG][hotfolder: {folder}] Effective config loaded (per-hotfolder):\n{json.dumps(config, indent=2)}")
        out_subfolder.mkdir(parents=True, exist_ok=True)
        while self.running:
            try:
                self.handle_hotfolder(folder, out_subfolder, hotfolder_debug)
            except Exception as e:
                logger = get_hotfolder_logger(folder)
                logger.error(f"Unhandled error in hotfolder thread: {e}")
            time.sleep(config.get("scan_interval", 10))

    def handle_hotfolder(self, folder, out_folder, hotfolder_debug=None):
        # Determine debug mode for this hotfolder
        if hotfolder_debug is None:
            config = get_effective_config(folder, self.global_config)
            hotfolder_debug = config.get("debug", self.debug)
        else:
            config = get_effective_config(folder, self.global_config)
        debug_enabled = self.debug or hotfolder_debug
        if debug_enabled:
            self._debug_print(folder, "handle_hotfolder called.", debug_enabled=debug_enabled)
        # Never execute or import code from the hotfolder
        for f in folder.iterdir():
            if f.suffix in {'.py', '.pyc', '.pyo', '.sh', '.bash', '.zsh', '.pl', '.rb', '.php', '.js', '.exe', '.dll', '.so', '.dylib'}:
                continue  # Just skip, never execute or import
        cleanup_processed_json(folder)
        logger = get_hotfolder_logger(folder, retention_days=config.get("log_retention", 7))
        resting_time = config.get("resting_time", 300)
        dissolve_folders = config.get("dissolve_folders", False)
        metadata = config.get("metadata", False)
        metadata_field = config.get("metadata_field", None)
        keep_copy = self.validate_bool(config.get("keep_copy", False), "keep_copy", False)
        ignore_updates = self.validate_bool(config.get("ignore_updates", False), "ignore_updates", False)
        retention = self.validate_bool(config.get("retention", False), "retention", False)
        retention_cleanup_time = config.get("retention_cleanup_time", 1440)
        update_mtime = config.get("update_mtime", True)
        now = time.time()
        config_dir = folder / ".config"
        processed = load_processed(config_dir)
        seen = load_seen(config_dir)
        files = [f for f in folder.iterdir() if not f.name.startswith('.')]
        changed = False
        for idx, f in enumerate(files):
            rel = str(f.relative_to(folder))
            # 1. Add to seen if new
            if rel not in seen:
                seen[rel] = now
                changed = True
                # Add a blank line before each new ARRIVED group except the first
                if idx > 0:
                    logger.info("")
                self.log_action(logger, folder, "ARRIVED", f"New file/folder: {rel}")
                # If it's a directory, recursively log all contained files
                f_path = folder / rel
                if f_path.is_dir():
                    for subfile in f_path.rglob('*'):
                        if subfile.is_file():
                            subrel = str(subfile.relative_to(folder))
                            # Indent CONTAINS lines for clarity
                            logger.info(f"    [CONTAINS] {subrel}")
            # 2. Check if stable
            seen_time = seen[rel]
            stable = (now - seen_time) >= resting_time
            if stable:
                # 3. If not processed, process and mark as processed
                if rel not in processed:
                    if debug_enabled:
                        self._debug_print(folder, f"[PROCESSING] {rel} is stable, processing now.", debug_enabled=debug_enabled)
                    moved_count = move_hotfolder_contents(
                        folder, out_folder, dissolve_folders, metadata, metadata_field, logger, keep_copy, ignore_updates, update_mtime)
                    processed[rel] = {"processed_time": now}
                    changed = True
                    self.log_action(logger, folder, "PROCESSED", f"Processed {rel}, moved_count={moved_count}")
            # 4. Log status
            processed_time = processed[rel]["processed_time"] if rel in processed else None
            age = (now - processed_time) if processed_time else None
            if debug_enabled:
                self._debug_print(folder, f"File: {f}, seen_time: {seen_time}, stable: {stable}, processed_time: {processed_time}, age: {age if age is not None else 'N/A'}", debug_enabled=debug_enabled)
        # 5. Retention cleanup
        if retention and keep_copy and retention_cleanup_time > 0:
            to_delete = []
            for rel, entry in processed.items():
                processed_time = entry.get("processed_time")
                if processed_time and (now - processed_time) > (retention_cleanup_time * 60):
                    to_delete.append(rel)
            for rel in to_delete:
                f = folder / rel
                try:
                    if f.is_dir():
                        shutil.rmtree(f)
                    else:
                        f.unlink()
                    self.log_action(logger, folder, "RETENTION", f"Deleted {rel} from IN after {retention_cleanup_time} minutes due to retention policy.")
                    del processed[rel]
                    if rel in seen:
                        del seen[rel]
                    changed = True
                except Exception as e:
                    self.log_action(logger, folder, "ERROR", f"Exception while deleting {rel}: {e}", level="error")
                    logger.error(f"[RETENTION CLEANUP] Failed to delete {rel}: {e}")
        # 6. Save state
        if changed:
            save_seen(config_dir, seen)
            save_processed(config_dir, processed)
        # Clean up processed/seen if empty
        cleanup_processed_json(folder)

    def _debug_print(self, folder, message, debug_enabled=None):
        if debug_enabled is None:
            debug_enabled = self.debug
        if debug_enabled:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[DEBUG][{ts}][hotfolder: {folder}] {message}")

    def log_action(self, logger, folder, action, details, level="info"):
        msg = f"[HOTFOLDER: {folder}] [{action}] {details}"
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