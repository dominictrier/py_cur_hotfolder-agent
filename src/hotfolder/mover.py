import shutil
from pathlib import Path
import os
import json
import time
from hotfolder.utils import is_image_file, resolve_metadata_field
from iptcinfo3 import IPTCInfo

def write_metadata(file_path, metadata_field, value, logger):
    try:
        info = IPTCInfo(file_path, force=True)
        # Remove 'IPTC:' prefix for iptcinfo3
        field = metadata_field.split(':')[-1]
        info[field] = value
        info.save()
        logger.info(f"Wrote metadata {metadata_field}='{value}' to {file_path}")
    except Exception as e:
        logger.error(f"Failed to write metadata to {file_path}: {e}")

def load_processed(config_dir):
    config_dir.mkdir(exist_ok=True)
    processed_file = config_dir / ".processed.json"
    if processed_file.exists():
        try:
            with open(processed_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_processed(config_dir, processed):
    config_dir.mkdir(exist_ok=True)
    processed_file = config_dir / ".processed.json"
    if processed:
        with open(processed_file, "w") as f:
            json.dump(processed, f, indent=2)
    else:
        if processed_file.exists():
            processed_file.unlink()

def load_seen(config_dir):
    config_dir.mkdir(exist_ok=True)
    seen_file = config_dir / ".seen.json"
    if seen_file.exists():
        try:
            with open(seen_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_seen(config_dir, seen):
    config_dir.mkdir(exist_ok=True)
    seen_file = config_dir / ".seen.json"
    with open(seen_file, "w") as f:
        json.dump(seen, f, indent=2)

def get_all_items(folder):
    # Recursively get all files and folders (relative to folder)
    items = []
    for root, dirs, files in os.walk(folder):
        for name in files:
            path = Path(root) / name
            rel = path.relative_to(folder)
            items.append(str(rel))
        for name in dirs:
            path = Path(root) / name
            rel = path.relative_to(folder)
            items.append(str(rel))
    return items

def move_hotfolder_contents(src_folder, dst_folder, dissolve_folders=False, metadata=False, metadata_field=None, logger=None, keep_copy=False, ignore_updates=False, update_mtime=True):
    if logger:
        logger.info(f"[DEBUG] move_hotfolder_contents called: src_folder={src_folder}, dst_folder={dst_folder}, keep_copy={keep_copy}, ignore_updates={ignore_updates}, update_mtime={update_mtime}")
    src_folder = Path(src_folder)
    dst_folder = Path(dst_folder)
    config_dir = src_folder / ".config"
    processed = load_processed(config_dir)
    current_items = get_all_items(src_folder)
    # Clean up processed: remove entries for files/folders no longer in IN
    removed_entries = set(processed.keys()) - set(current_items)
    if removed_entries and logger:
        for entry in removed_entries:
            logger.info(f"Removed entry from .processed.json (file/folder missing): {entry}")
    processed = {k: v for k, v in processed.items() if k in current_items}
    moved_count = 0
    # For each item in src_folder
    for item in src_folder.iterdir():
        if logger:
            logger.info(f"[DEBUG] Processing item: {item}, is_dir={item.is_dir()}, keep_copy={keep_copy}")
        if item.name.startswith('.'):
            continue  # Skip .config, .log, etc.
        dest = dst_folder / item.name
        rel_path = str(item.relative_to(src_folder))
        mtime = item.stat().st_mtime
        already_processed = rel_path in processed and processed[rel_path] == mtime
        if keep_copy:
            if ignore_updates:
                if already_processed:
                    if logger:
                        logger.info(f"[DEBUG] Skipping already processed item (ignore_updates): {item}")
                    continue  # Skip, already processed
            else:
                # If not ignore_updates, re-copy if mtime changed
                if already_processed:
                    # If mtime is the same, skip
                    if logger:
                        logger.info(f"[DEBUG] Skipping already processed item: {item}")
                    continue
        if item.is_dir():
            if dissolve_folders:
                # TODO: Flatten and copy files only
                pass
            else:
                if keep_copy:
                    if logger:
                        logger.info(f"[DEBUG] Copying directory: {item} -> {dest}")
                    shutil.copytree(str(item), str(dest), dirs_exist_ok=True)
                else:
                    if logger:
                        logger.info(f"[DEBUG] Moving directory: {item} -> {dest}")
                    shutil.move(str(item), str(dest))
                moved_count += 1
                # Touch the folder after moving/copying if update_mtime is True
                if update_mtime:
                    try:
                        os.utime(str(dest), None)
                    except Exception as e:
                        if logger:
                            logger.warning(f"Failed to update mtime for {dest}: {e}")
        else:
            # METADATA HANDLING
            if metadata and is_image_file(item):
                if not metadata_field:
                    if logger:
                        logger.error(f"No metadata_field provided for {item}, cannot write metadata, processing anyway.")
                else:
                    iptc_field = resolve_metadata_field(metadata_field)
                    if not iptc_field:
                        if logger:
                            logger.error(f"Could not resolve metadata_field '{metadata_field}' for {item}, processing anyway.")
                    else:
                        write_metadata(str(item), iptc_field, str(item.resolve()), logger)
            if keep_copy:
                if logger:
                    logger.info(f"[DEBUG] Copying file: {item} -> {dest}")
                shutil.copy2(str(item), str(dest))
            else:
                if logger:
                    logger.info(f"[DEBUG] Moving file: {item} -> {dest}")
                shutil.move(str(item), str(dest))
            moved_count += 1
            # Touch the file after moving/copying if update_mtime is True
            if update_mtime:
                try:
                    os.utime(str(dest), None)
                except Exception as e:
                    if logger:
                        logger.warning(f"Failed to update mtime for {dest}: {e}")
        # Mark as processed (always use dict with processed_time)
        processed[rel_path] = {'processed_time': time.time()}
    # Always save the cleaned processed dict, even if nothing was moved
    save_processed(config_dir, processed)
    # Remove .processed.json and .seen.json if there are no more entries to monitor
    if not processed:
        processed_file = config_dir / ".processed.json"
        if processed_file.exists():
            processed_file.unlink()
            if logger:
                logger.info("Removed .processed.json (no more files/folders to monitor)")
        # Remove .seen.json if the folder is empty (excluding .config and .log)
        seen_file = config_dir / ".seen.json"
        if seen_file.exists():
            non_hidden = [f for f in src_folder.iterdir() if not f.name.startswith('.')]
            if not non_hidden:
                try:
                    seen_file.unlink()
                    if logger:
                        logger.info("Removed .seen.json (folder is empty)")
                except Exception:
                    pass
    return moved_count
    # TODO: Handle more metadata if needed 

def cleanup_processed_json(hotfolder_path):
    hotfolder_path = Path(hotfolder_path)
    config_dir = hotfolder_path / ".config"
    processed = load_processed(config_dir)
    current_items = get_all_items(hotfolder_path)
    # Clean up processed: remove entries for files/folders no longer in IN
    removed_entries = set(processed.keys()) - set(current_items)
    logger = None
    try:
        from hotfolder.logger import get_hotfolder_logger
        logger = get_hotfolder_logger(hotfolder_path)
    except Exception:
        pass
    if removed_entries and logger:
        for entry in removed_entries:
            logger.info(f"Removed entry from .processed.json (file/folder missing): {entry}")
    processed = {k: v for k, v in processed.items() if k in current_items}
    save_processed(config_dir, processed)
    # Remove .processed.json and .seen.json if there are no more entries to monitor
    if not processed:
        processed_file = config_dir / ".processed.json"
        if processed_file.exists():
            processed_file.unlink()
            if logger:
                logger.info("Removed .processed.json (no more files/folders to monitor)")
        # Remove .seen.json if the folder is empty (excluding .config and .log)
        seen_file = config_dir / ".seen.json"
        if seen_file.exists():
            non_hidden = [f for f in hotfolder_path.iterdir() if not f.name.startswith('.')]
            if not non_hidden:
                try:
                    seen_file.unlink()
                    if logger:
                        logger.info("Removed .seen.json (folder is empty)")
                except Exception:
                    pass