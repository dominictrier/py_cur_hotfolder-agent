# Hotfolder System

![version](https://img.shields.io/badge/version-1.9.2-blue)

## Overview
This Python hotfolder system monitors one or more input directories for new files or folders, processes them according to configurable rules, and moves or copies them to output directories. It is designed for 24/7 unattended operation and supports per-hotfolder configuration, logging, metadata writing for image files, and advanced file retention/copying logic.

## Features
- Monitors multiple hotfolder roots (IN directories) for new subfolders (hotfolders)
- Each hotfolder can have its own `.config/config.yml` and `.log` directory
- Configurable resting time (stability before processing)
- Automatic creation of config example files
- Logging with rotation and retention
- Metadata writing to image files (IPTC fields)
- Dynamic detection of new/removed hotfolders
- Configurable scan interval for both global and per-hotfolder polling
- **Keep files**, **ignore updates**, and **update mtime** options for advanced copy/retention logic
- **Skips `.DS_Store` and `thumbs.db` files** (if enabled in config) when copying/moving to OUT, so OUT is always clean of these system files.

## Configuration

### Global Config (`config.yml`)

The global config is a YAML file with grouped settings. Example:

```yaml
hotfolders:
  - /path/to/hotfolders/IN
schedule:
  scan_interval: 10
  resting_time: 1800
retention:
  cleanup: true
  keep_copy: true
  cleanup_time: 2880
structure:
  dissolve_folders: false
metadata:
  enabled: false
  field: ""
auto_cleanup:
  ds_store: true
  thumbs_db: true
mtime:
  update_mtime: true
logging:
  log_retention: 7
debugging:
  debug: true
heartbeat:
  heartbeat_enabled: false
```

### Per-Hotfolder Config

Each hotfolder can override any global config value by providing its own `.config/config.yml` using the same grouped structure as above.
If missing, a `.config/config.yml.example` is created and the global config is used.

### State Management

- State is tracked in a SQLite database (`.hotfolder_state.db`) in each hotfolder.
- No `.seen.json` or `.processed.json` files are used.
- All job and file tracking is robust, auditable, and local to each hotfolder.

### Logging

- Logs are written to `.log/<hotfolder>.log` in each hotfolder.
- Debug logs are written to `.log/<hotfolder>.debug.log` if debug is enabled.

### Example Directory Structure

```
hotfolder_test/
  test1/
    .config/
      config.yml
      config.yml.example
    .log/
      test1.log
      test1.debug.log
    .hotfolder_state.db
  test1_out/
  test2/
    .config/
      config.yml
      config.yml.example
    .log/
      test2.log
      test2.debug.log
    .hotfolder_state.db
```

### Notes

- All configuration is now YAML-based.
- All state is managed in SQLite, not JSON files.
- OUT folders and config examples are created automatically for each detected hotfolder.

## Keep Files & Ignore Updates Logic
- If `keep_copy` is true:
  - Files/folders are **copied** to OUT, not moved.
  - Originals remain in IN.
- If `ignore_updates` is true:
  - After a file/folder is processed once, future changes/additions are ignored.
  - If a file/folder is deleted from IN, it is also removed from the `.hotfolder_state.db` tracking file.
- If `ignore_updates` is false:
  - If a file/folder is updated or a new file is added, the whole folder is copied again after the new resting time is up.
- The `.hotfolder_state.db` file in each hotfolder's `.config` directory tracks what has been processed and when files/folders were first seen. This file is now robustly cleaned up only when the folder is truly empty, preventing repeated log messages and ensuring correct state tracking.

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
- Ensure all config fields are present in `config.yml` and per-hotfolder configs.
- Check logs in each hotfolder's `.log` directory for errors.
- If a hotfolder is not detected, ensure it is a direct subfolder of the IN directory and not hidden.

## License
MIT

## Versioning

The project version is tracked in `src/hotfolder/__init__.py` as `__version__`. Please update this value and the badge above for each release.

## Housecleaning in 1.9.0
- Removed unused heartbeat logic and files (heartbeat.py, heartbeat.txt)
- Cleaned up all references to obsolete config and state files

## Configuration Style

All new configuration options should be grouped under a descriptive key (e.g., `cleaning`, `interval`, `logging`). This keeps the config organized and scalable.

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

## **Strict config validation**: All config fields are strictly type-checked and required in per-hotfolder configs. If any required key is missing or has the wrong type, hotfolder processing fails and an error is logged. Global config is only used if no per-hotfolder config is present.

## 1.9.2 Minor update
- Added heartbeat_enabled config option to control writing a heartbeat.txt file for external monitoring.

### Heartbeat

The global config now supports a heartbeat option:

```yaml
heartbeat:
  heartbeat_enabled: false   # Enable writing a heartbeat.txt file for external monitoring
```

If enabled, the watcher will periodically write a `heartbeat/heartbeat.txt` file with a timestamp, which can be used by external scripts or monitoring tools to check if the agent is alive.
