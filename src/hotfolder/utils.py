import os
import time
from pathlib import Path

def is_folder_stable(folder_path, resting_time):
    folder_path = Path(folder_path)
    now = time.time()
    stable = True
    for root, dirs, files in os.walk(folder_path):
        # Skip .config and .log folders at any level
        dirs[:] = [d for d in dirs if d not in ['.config', '.log']]
        for name in files + dirs:
            if name in ['.config', '.log']:
                continue
            path = Path(root) / name
            mtime = path.stat().st_mtime
            print(f"[DEBUG] Checking {path}: mtime={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}, now={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}, delta={now - mtime:.1f}s (resting_time={resting_time}s)")
            if now - mtime < resting_time:
                stable = False
    return stable

def is_image_file(file_path):
    image_exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
    return Path(file_path).suffix.lower() in image_exts

def normalize_path(path_str):
    """
    Fixes escaped spaces in paths (e.g., replaces '\\ ' with ' ').
    Use this to clean up paths from the terminal, especially on macOS.
    """
    return path_str.replace('\\ ', ' ') 