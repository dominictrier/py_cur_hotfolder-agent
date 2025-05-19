import shutil
from pathlib import Path
import os
import json
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
    processed_file = config_dir / ".processed.json"
    if processed_file.exists():
        try:
            with open(processed_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_processed(config_dir, processed):
    processed_file = config_dir / ".processed.json"
    with open(processed_file, "w") as f:
        json.dump(processed, f, indent=2)

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

def move_hotfolder_contents(src_folder, dst_folder, dissolve_folders=False, metadata=False, metadata_field=None, logger=None, keep_files=False, ignore_updates=False):
    src_folder = Path(src_folder)
    dst_folder = Path(dst_folder)
    config_dir = src_folder / ".config"
    processed = load_processed(config_dir)
    current_items = get_all_items(src_folder)
    # Clean up processed: remove entries for files/folders no longer in IN
    processed = {k: v for k, v in processed.items() if k in current_items}
    moved_count = 0
    # For each item in src_folder
    for item in src_folder.iterdir():
        if item.name.startswith('.'):
            continue  # Skip .config, .log, etc.
        dest = dst_folder / item.name
        rel_path = str(item.relative_to(src_folder))
        mtime = item.stat().st_mtime
        already_processed = rel_path in processed and processed[rel_path] == mtime
        if keep_files:
            if ignore_updates:
                if already_processed:
                    continue  # Skip, already processed
            else:
                # If not ignore_updates, re-copy if mtime changed
                if already_processed:
                    # If mtime is the same, skip
                    continue
        if item.is_dir():
            if dissolve_folders:
                # TODO: Flatten and copy files only
                pass
            else:
                if keep_files:
                    shutil.copytree(str(item), str(dest), dirs_exist_ok=True)
                else:
                    shutil.move(str(item), str(dest))
                moved_count += 1
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
            if keep_files:
                shutil.copy2(str(item), str(dest))
            else:
                shutil.move(str(item), str(dest))
            moved_count += 1
        # Mark as processed
        processed[rel_path] = mtime
    # Always save the cleaned processed dict, even if nothing was moved
    save_processed(config_dir, processed)
    # Remove .processed.json if there are no more entries to monitor
    if not processed:
        processed_file = config_dir / ".processed.json"
        if processed_file.exists():
            processed_file.unlink()
    return moved_count
    # TODO: Handle more metadata if needed 

def cleanup_processed_json(hotfolder_path):
    hotfolder_path = Path(hotfolder_path)
    config_dir = hotfolder_path / ".config"
    processed = load_processed(config_dir)
    current_items = get_all_items(hotfolder_path)
    # Clean up processed: remove entries for files/folders no longer in IN
    processed = {k: v for k, v in processed.items() if k in current_items}
    save_processed(config_dir, processed)
    # Remove .processed.json if there are no more entries to monitor
    if not processed:
        processed_file = config_dir / ".processed.json"
        if processed_file.exists():
            processed_file.unlink() 