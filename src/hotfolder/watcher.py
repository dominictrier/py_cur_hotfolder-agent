from hotfolder.config import load_global_config, get_effective_config
from hotfolder.logger import get_hotfolder_logger
from hotfolder.utils import is_folder_stable, normalize_path
from hotfolder.mover import move_hotfolder_contents, cleanup_processed_json, load_processed
import os
import time
from pathlib import Path
import threading
from datetime import datetime, timedelta
import json
import sys
from hotfolder.heartbeat import write_heartbeat

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
            print("[DEBUG] Raw global config loaded:")
            print(json.dumps(self.global_config, indent=2))
        # Normalize all hotfolder root paths to fix escaped spaces
        self.hotfolder_roots = [normalize_path(hf) for hf in self.global_config.get("hotfolders", [])]
        if self.debug:
            print(f"[DEBUG] Normalized hotfolder roots list: {self.hotfolder_roots}")
        self.running = False
        self.threads = {}  # {subfolder_path: thread}
        self.last_status = {}
        self.lock = threading.Lock()

    def run(self):
        self.running = True
        if self.debug:
            print("Starting dynamic hotfolder watcher...")
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
        hotfolder_pairs = {}  # {in_subfolder: out_root}
        for root in self.hotfolder_roots:
            root_path = Path(root).resolve()
            out_root = root_path.parent / f"{root_path.name}_out"
            if not root_path.exists():
                if self.debug:
                    print(f"[WARNING] Hotfolder root does not exist: {root_path}")
                continue
            out_root.mkdir(parents=True, exist_ok=True)
            for subfolder in root_path.iterdir():
                if subfolder.is_dir() and not subfolder.name.startswith('.'):
                    current_hotfolders.add(str(subfolder))
                    hotfolder_pairs[str(subfolder)] = out_root
        # Start threads for new hotfolders
        with self.lock:
            for folder in current_hotfolders:
                if folder not in self.threads:
                    if self.debug:
                        print(f"[INFO] Starting watcher for new hotfolder: {folder}")
                    out_root = hotfolder_pairs[folder]
                    t = threading.Thread(target=self.watch_hotfolder, args=(folder, out_root), daemon=True)
                    t.start()
                    self.threads[folder] = t
            # Remove threads for hotfolders that no longer exist
            removed = [f for f in self.threads if f not in current_hotfolders]
            for folder in removed:
                if self.debug:
                    print(f"[INFO] Hotfolder removed or no longer exists: {folder}")
                # Remove OUT subfolder if empty
                in_folder = Path(folder)
                out_root = in_folder.parent.parent / f"{in_folder.parent.name}_out"
                out_subfolder = out_root / in_folder.name
                if out_subfolder.exists() and out_subfolder.is_dir():
                    try:
                        if not any(out_subfolder.iterdir()):
                            out_subfolder.rmdir()
                    except Exception:
                        pass
                del self.threads[folder]
        if self.debug:
            print(f"[DEBUG] Currently watched hotfolders: {list(self.threads.keys())}")

    def watch_hotfolder(self, folder_path, out_root):
        folder = Path(folder_path).resolve()
        config = get_effective_config(folder, self.global_config)
        out_subfolder = Path(out_root) / folder.name
        out_subfolder.mkdir(parents=True, exist_ok=True)
        while self.running:
            try:
                self.handle_hotfolder(folder, out_subfolder)
            except Exception as e:
                logger = get_hotfolder_logger(folder)
                logger.error(f"Unhandled error in hotfolder thread: {e}")
            time.sleep(config.get("scan_interval", 10))

    def handle_hotfolder(self, folder, out_folder):
        # Never execute or import code from the hotfolder
        for f in folder.iterdir():
            if f.suffix in {'.py', '.pyc', '.pyo', '.sh', '.bash', '.zsh', '.pl', '.rb', '.php', '.js', '.exe', '.dll', '.so', '.dylib'}:
                continue  # Just skip, never execute or import
        cleanup_processed_json(folder)
        config = get_effective_config(folder, self.global_config)
        # Autoclean .DS_Store files if enabled
        if config.get("autoclean", True):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower() == ".ds_store":
                        ds_path = Path(root) / file
                        try:
                            ds_path.unlink()
                        except Exception as e:
                            if self.debug:
                                print(f"[WARNING] Could not remove {ds_path}: {e}")
        logger = get_hotfolder_logger(folder, retention_days=config.get("log_retention", 7))
        resting_time = config.get("resting_time", 300)
        dissolve_folders = config.get("dissolve_folders", False)
        metadata = config.get("metadata", False)
        metadata_field = config.get("metadata_field", None)
        keep_files = config.get("keep_files", False)
        ignore_updates = config.get("ignore_updates", False)
        now = time.time()
        files = [f for f in folder.iterdir() if not f.name.startswith('.')]
        if not files:
            return
        # Log new arrivals
        config_dir = folder / ".config"
        processed = load_processed(config_dir)
        current_names = set(str(f.relative_to(folder)) for f in files)
        processed_names = set(processed.keys())
        new_arrivals = current_names - processed_names
        for name in new_arrivals:
            logger.info(f"New file/folder arrived: {name}")
            abs_path = folder / name
            if abs_path.is_dir():
                for root, dirs, files_in_dir in os.walk(abs_path):
                    rel_root = Path(root).relative_to(folder)
                    for d in dirs:
                        logger.info(f"   Contains: {rel_root / d}/")
                    for f_ in files_in_dir:
                        logger.info(f"   Contains: {rel_root / f_}")
        if self.debug:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hotfolder {folder}: files found: {[f.name for f in files]}")
        # Find the most recent mtime
        latest_mtime = max(f.stat().st_mtime for f in files)
        stable_at = latest_mtime + resting_time
        stable_dt = datetime.fromtimestamp(stable_at)
        is_stable = is_folder_stable(folder, resting_time)
        last = self.last_status.get(str(folder), {})
        try:
            if is_stable:
                if not last.get('stable', False):
                    if self.debug:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hotfolder {folder}: STABLE, will pull now.")
                moved_count = move_hotfolder_contents(folder, out_folder, dissolve_folders, metadata, metadata_field, logger, keep_files, ignore_updates)
                if moved_count > 0:
                    logger.info(f"Folder {folder} is stable. Moving contents to {out_folder}.")
                    logger.info(f"Move complete for {folder}. {moved_count} item(s) moved.")
                self.last_status[str(folder)] = {'stable': True}
            else:
                if last.get('stable', True) or last.get('stable_at') != stable_at:
                    if self.debug:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hotfolder {folder}: NOT STABLE, if stable will pull at {stable_dt}.")
                self.last_status[str(folder)] = {'stable': False, 'stable_at': stable_at}
                # Only log waiting if there are files to process
                # logger.info(f"Folder {folder} is not yet stable. Waiting.")
        except Exception as e:
            logger.error(f"Error processing {folder}: {e}") 