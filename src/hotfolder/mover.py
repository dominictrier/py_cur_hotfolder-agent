import shutil
from pathlib import Path
import os
import time
from hotfolder.utils import is_image_file
from iptcinfo3 import IPTCInfo

def write_metadata(file_path, metadata_field, value, logger):
    try:
        info = IPTCInfo(file_path, force=True)
        field = metadata_field
        # Try as provided
        try:
            info[field] = value
            info.save()
            logger.info(f"Wrote metadata '{field}'='{value}' to {file_path}")
            logger.debug(f"[METADATA] Used provided field '{field}' for {file_path}")
            return
        except Exception as e:
            logger.debug(f"[METADATA] Provided field '{field}' failed for {file_path}: {e}")
        # Fallback: scan for a matching key
        found_key = None
        for k in info._data.keys():
            if k.lower() == field.lower() or field.lower() in k.lower():
                found_key = k
                break
        if found_key:
            try:
                info[found_key] = value
                info.save()
                logger.info(f"Wrote metadata '{found_key}'='{value}' to {file_path} (using fallback for '{field}')")
                logger.debug(f"[METADATA] Provided field '{field}' not found, used '{found_key}' for {file_path}")
                return
            except Exception as e:
                logger.error(f"Failed to write metadata to {file_path} using fallback key '{found_key}': {e}")
                logger.debug(f"[METADATA] Fallback field '{found_key}' failed for {file_path}: {e}")
        # If still not found
        logger.error(f"Failed to write metadata: field '{field}' not found in {file_path}. Available keys: {list(info._data.keys())}")
        logger.debug(f"[METADATA] No matching field for '{field}' in {file_path}. Skipping metadata write.")
    except Exception as e:
        logger.error(f"Failed to open or process {file_path} for metadata: {e}")
        logger.debug(f"[METADATA] Exception in write_metadata for {file_path}: {e}")

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

def move_hotfolder_contents(src_folder, dst_folder, dissolve_folders=False, metadata=False, metadata_field=None, logger=None, keep_copy=False, ignore_updates=False, update_mtime=True, ds_store=True, thumbs_db=True):
    if logger:
        logger.info(f"move_hotfolder_contents called: src_folder={src_folder}, dst_folder={dst_folder}, keep_copy={keep_copy}, ignore_updates={ignore_updates}, update_mtime={update_mtime}, ds_store={ds_store}, thumbs_db={thumbs_db}")
    src_folder = Path(src_folder)
    dst_folder = Path(dst_folder)
    moved_count = 0
    marked_for_deletion = []
    # For each item in src_folder
    for item in src_folder.iterdir():
        if logger:
            logger.info(f"Processing item: {item}, is_dir={item.is_dir()}, keep_copy={keep_copy}")
        if item.name.startswith('.'):
            continue  # Skip .config, .log, etc.
        # Respect config for ds_store and thumbs_db
        if (ds_store and item.name == '.DS_Store') or (thumbs_db and item.name.lower() == 'thumbs.db'):
            if logger:
                logger.info(f"Skipping system file: {item}")
            continue  # Never copy/move .DS_Store or Thumbs.db to OUT if enabled
        dest = dst_folder / item.name
        rel_path = str(item.relative_to(src_folder))
        mtime = item.stat().st_mtime
        if item.is_file():
            if keep_copy:
                if logger:
                    logger.info(f"Copying file: {item} -> {dest}")
                shutil.copy2(str(item), str(dest))
            else:
                if logger:
                    logger.info(f"Moving file: {item} -> {dest}")
                shutil.move(str(item), str(dest))
            moved_count += 1
            if update_mtime:
                try:
                    os.utime(str(dest), None)
                except Exception as e:
                    if logger:
                        logger.warning(f"Failed to update mtime for {dest}: {e}")
        elif item.is_dir():
            if dissolve_folders:
                # Flatten: move/copy all files in this subfolder directly to dst_folder
                for root, dirs, files in os.walk(item):
                    for fname in files:
                        if (ds_store and fname == '.DS_Store') or (thumbs_db and fname.lower() == 'thumbs.db'):
                            if logger:
                                logger.info(f"Skipping system file: {fname}")
                            continue
                        src_file = Path(root) / fname
                        dest_file = dst_folder / fname
                        if keep_copy:
                            if logger:
                                logger.info(f"Copying file (dissolve): {src_file} -> {dest_file}")
                            shutil.copy2(str(src_file), str(dest_file))
                        else:
                            if logger:
                                logger.info(f"Moving file (dissolve): {src_file} -> {dest_file}")
                            shutil.move(str(src_file), str(dest_file))
                        moved_count += 1
                        if update_mtime:
                            try:
                                os.utime(str(dest_file), None)
                            except Exception as e:
                                if logger:
                                    logger.warning(f"Failed to update mtime for {dest_file}: {e}")
                # After moving/copying, if the folder is now empty, mark for deletion
                if not any(item.iterdir()):
                    marked_for_deletion.append(item.name)
            else:
                if keep_copy:
                    if logger:
                        logger.info(f"Copying directory: {item} -> {dest}")
                    def ignore_system_files(dir, files):
                        ignore = []
                        if ds_store:
                            ignore += [f for f in files if f == '.DS_Store']
                        if thumbs_db:
                            ignore += [f for f in files if f.lower() == 'thumbs.db']
                        return ignore
                    shutil.copytree(str(item), str(dest), dirs_exist_ok=True, ignore=ignore_system_files)
                else:
                    if logger:
                        logger.info(f"Moving directory: {item} -> {dest}")
                    shutil.move(str(item), str(dest))
                    for root, dirs, files in os.walk(dest):
                        for f in files:
                            if (ds_store and f == '.DS_Store') or (thumbs_db and f.lower() == 'thumbs.db'):
                                try:
                                    os.remove(os.path.join(root, f))
                                    if logger:
                                        logger.info(f"Removed system file from OUT after move: {os.path.join(root, f)}")
                                except Exception as e:
                                    if logger:
                                        logger.warning(f"Failed to remove system file from OUT: {e}")
                moved_count += 1
                if update_mtime:
                    try:
                        os.utime(str(dest), None)
                    except Exception as e:
                        if logger:
                            logger.warning(f"Failed to update mtime for {dest}: {e}")
    return moved_count, marked_for_deletion
    # TODO: Handle more metadata if needed 