# Hotfolder System

![version](https://img.shields.io/badge/version-1.5.0-blue)

## Overview
This Python hotfolder system monitors one or more input directories for new files or folders, processes them according to configurable rules, and moves or copies them to output directories. It is designed for 24/7 unattended operation and supports per-hotfolder configuration, logging, metadata writing for image files, and advanced file retention/copying logic.

## Features
- Monitors multiple hotfolder roots (IN directories) for new subfolders (hotfolders)
- Each hotfolder can have its own `.config/config.json` and `.log` directory
- Configurable resting time (stability before processing)
- Automatic creation of config example files
- Logging with rotation and retention
- Metadata writing to image files (IPTC fields)
- Dynamic detection of new/removed hotfolders
- Configurable scan interval for both global and per-hotfolder polling
- **Keep files** and **ignore updates** options for advanced copy/retention logic

## Configuration

### Global Config (`config.json`)
Example:
```json
{
  "hotfolders": [
    "/path/to/hotfolders/IN"
  ],
  "timing": {
    "scan_interval": 10,
    "resting_time": 300
  },
  "flattening": {
    "dissolve_folders": false
  },
  "metadata": {
    "metadata": false,
    "metadata_field": ""
  },
  "logging": {
    "log_retention": 7
  },
  "buffering": {
    "keep_files": false,
    "ignore_updates": false
  },
  "cleaning": {
    "autoclean": true
  }
}
```
- `hotfolders`: List of IN directories to monitor for hotfolders
- `timing`: Timing-related options
  - `scan_interval`: How often (in seconds) to rescan for new/removed hotfolders and poll each hotfolder
  - `resting_time`: Seconds a folder must be stable before processing
- `flattening`:
  - `dissolve_folders`: If true, flattens folder structure when moving/copying
- `metadata`: Metadata options
  - `metadata`: If true, writes metadata to image files
  - `metadata_field`: The IPTC field to write the file path to (e.g., `Headline` or `IPTC:Headline`)
- `logging`: Logging options
  - `log_retention`: Log retention in days
- `buffering`: File retention/copying options
  - `keep_files`: If true, files/folders are copied (not moved) to OUT and originals remain in IN
  - `ignore_updates`: If true, after a file/folder is processed once, future changes/additions are ignored
  - **Note:** Per-hotfolder config can override global config. To enable copying for a specific hotfolder, set `keep_files: true` in its `.config/config.json`.
- `cleaning`: Cleaning-related options
  - `autoclean`: If true, automatically removes `.DS_Store` files from hotfolders

### Per-Hotfolder Config
Each hotfolder can override any global config value by providing its own `.config/config.json` using the same grouped structure as above.
If missing, a `.config/config.json.example` is created and the global config is used.

## Keep Files & Ignore Updates Logic
- If `keep_files` is true:
  - Files/folders are **copied** to OUT, not moved.
  - Originals remain in IN.
- If `ignore_updates` is true:
  - After a file/folder is processed (copied), future changes/additions are ignored.
  - If a file/folder is deleted from IN, it is also removed from the `.processed.json` tracking file.
- If `ignore_updates` is false:
  - If a file/folder is updated or a new file is added, the whole folder is copied again after the new resting time is up.
- The `.processed.json` file in each hotfolder's `.config` directory tracks what has been processed and is automatically cleaned up if files/folders are deleted from IN.

## Metadata Feature
- If `metadata` is `true` and the file is an image (`.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`):
  - If `metadata_field` is empty, an error is logged but the file is processed.
  - If `metadata_field` is provided, the full file path is written to that IPTC field.
  - If only a field name like `Headline` is given, the system tries to resolve it to `IPTC:Headline`.
  - If the field cannot be resolved, an error is logged but the file is processed.
- Uses `iptcinfo3` for IPTC metadata writing.

## Logging
- Each hotfolder has its own `.log/{hotfolder}.log` file.
- Log rotation and retention are configurable.
- All actions, errors, and metadata operations are logged.

## Dependencies
- Python 3.7+
- [Pillow](https://pypi.org/project/Pillow/)
- [iptcinfo3](https://pypi.org/project/iptcinfo3/)

Install dependencies:
```
pip install -r requirements.txt
```

## Running
```
python3 src/main.py
```

## Platform Notes
- Designed for macOS, but should work on Linux as well.
- Paths with spaces are supported (escaped or unescaped).

## Troubleshooting
- Ensure all config fields are present in `config.json` and per-hotfolder configs.
- Check logs in each hotfolder's `.log` directory for errors.
- If a hotfolder is not detected, ensure it is a direct subfolder of the IN directory and not hidden.

## License
MIT

## Versioning

The project version is tracked in `src/hotfolder/__init__.py` as `__version__`. Please update this value and the badge above for each release.

## Configuration Style

All new configuration options should be grouped under a descriptive key (e.g., `cleaning`, `timing`, `logging`). This keeps the config organized and scalable.

## Launchd Configuration

To keep your hotfolder script running continuously on macOS, you can use `launchd` with a proper `plist` file.

```xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.yourorg.hotfolder</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/python3</string>
    <string>/Path/to/py_cur_hotfolder-agent/src/main.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Path/to/py_cur_hotfolder-agent</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/hotfolder.out</string>
  <key>StandardErrorPath</key>
  <string>/tmp/hotfolder.err</string>
</dict>
</plist>
```

## Example Hotfolder Directory Structure

```
hotfolder/
├── actual_hotfolder_1/
├── actual_hotfolder_1_out/
```

- For each subfolder `xxx` in the IN root, an OUT folder `xxx_out` is created as a sibling in the same IN root.
