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

class HotfolderWatcher:
    def __init__(self):
        self.global_config = load_global_config()
        print("[DEBUG] Raw global config loaded:")
        print(json.dumps(self.global_config, indent=2))
        # Normalize all hotfolder root paths to fix escaped spaces
        self.hotfolder_roots = [normalize_path(hf) for hf in self.global_config.get("hotfolders", [])]
        print(f"[DEBUG] Normalized hotfolder roots list: {self.hotfolder_roots}")
        self.running = False
        self.threads = {}  # {subfolder_path: thread}
        self.last_status = {}
        self.lock = threading.Lock()

    def run(self):
        self.running = True
        print("Starting dynamic hotfolder watcher...")
        try:
            while self.running:
                self.scan_and_update_hotfolders()
                time.sleep(self.global_config.get("scan_interval", 10))
        except KeyboardInterrupt:
            self.running = False
            print("Shutting down watcher...")

    def scan_and_update_hotfolders(self):
        current_hotfolders = set()
        for root in self.hotfolder_roots:
            root_path = Path(root).resolve()
            if not root_path.exists():
                print(f"[WARNING] Hotfolder root does not exist: {root_path}")
                continue
            for subfolder in root_path.iterdir():
                if subfolder.is_dir() and not subfolder.name.startswith('.'):
                    current_hotfolders.add(str(subfolder))
        # Start threads for new hotfolders
        with self.lock:
            for folder in current_hotfolders:
                if folder not in self.threads:
                    print(f"[INFO] Starting watcher for new hotfolder: {folder}")
                    t = threading.Thread(target=self.watch_hotfolder, args=(folder,), daemon=True)
                    t.start()
                    self.threads[folder] = t
            # Optionally, stop threads for removed hotfolders (not implemented for simplicity)
            # Remove threads for hotfolders that no longer exist
            removed = [f for f in self.threads if f not in current_hotfolders]
            for folder in removed:
                print(f"[INFO] Hotfolder removed or no longer exists: {folder}")
                # No direct way to stop threads, but they will exit on next check if self.running is False
                del self.threads[folder]
        print(f"[DEBUG] Currently watched hotfolders: {list(self.threads.keys())}")

    def watch_hotfolder(self, folder_path):
        folder = Path(folder_path).resolve()
        config = get_effective_config(folder, self.global_config)
        out_root = folder.parent.parent / "OUT" / folder.name
        while self.running:
            self.handle_hotfolder(folder, out_root)
            time.sleep(config.get("scan_interval", 10))

    def handle_hotfolder(self, folder, out_folder):
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
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hotfolder {folder}: STABLE, will pull now.")
                moved_count = move_hotfolder_contents(folder, out_folder, dissolve_folders, metadata, metadata_field, logger, keep_files, ignore_updates)
                if moved_count > 0:
                    logger.info(f"Folder {folder} is stable. Moving contents to {out_folder}.")
                    logger.info(f"Move complete for {folder}. {moved_count} item(s) moved.")
                self.last_status[str(folder)] = {'stable': True}
            else:
                if last.get('stable', True) or last.get('stable_at') != stable_at:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hotfolder {folder}: NOT STABLE, if stable will pull at {stable_dt}.")
                self.last_status[str(folder)] = {'stable': False, 'stable_at': stable_at}
                # Only log waiting if there are files to process
                # logger.info(f"Folder {folder} is not yet stable. Waiting.")
        except Exception as e:
            logger.error(f"Error processing {folder}: {e}") 