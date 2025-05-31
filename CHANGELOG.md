# Changelog

## [1.9.2] - Heartbeat config option
- Added heartbeat_enabled config option to control writing a heartbeat.txt file for external monitoring
- Updated config files, example, and documentation

## [1.9.1] - Minor config and documentation update
- Updated config.yml and config.yml.example for clarity and consistency
- Updated README and version badge

## [1.9.0] - Housecleaning and removal of unused logic
- Removed unused heartbeat logic and files (`heartbeat.py`, `heartbeat.txt`)
- Cleaned up all references to obsolete config and state files (e.g., `.json`, `config.json`, etc.)
- Updated documentation and README to reflect these changes

## [1.8.0] - Major config and retention_cleanup_time cleanup update
- Refactored config structure and naming for clarity and future-proofing
- Added and validated new key: schedule.retention_cleanup_time (default: 1440 minutes)
- Retention_cleanup_time now only affects files kept via keep_copy
- Improved config validation and error reporting (prints in debug, logs for hotfolders)
- **Strict config validation and type checks for all config fields (per-hotfolder and global). If any required key is missing or has the wrong type, hotfolder processing fails and an error is logged.**
- **Retention_cleanup_time is now always in minutes (not seconds).**
- Updated all documentation and config examples to match new structure
- Bumped default version to 1.8.0

## [1.7.0] - Minor update
- Feature: Add per-hotfolder and global config option mtime.update_mtime (default: false) to control whether jobs (files/folders) are 'touched' (mtime updated) after moving/copying to OUT. Helps avoid 1970-mtime masking issues in OUT folders. Fully documented and configurable. 

## [1.6.0] - Minor update
- Robust cleanup of .seen.json and .processed.json: these files are now only deleted when the folder is truly empty, preventing repeated log messages and ensuring correct state tracking
- Bugfix: removed erroneous return statement that caused NameError in cleanup_processed_json

## [1.5.0] - Minor update
- Clarified documentation for per-hotfolder config and keep_copy behavior
- Ensured correct copying/moving logic based on config

## [1.4.0] - Minor update
- OUT folders are now created as siblings to each subfolder in the IN root, with _out appended to the name
- Updated documentation and example directory structure in README for clarity

## [1.3.0] - Minor update
- OUT root is now always a sibling of IN root with _out, and OUT subfolders mirror IN subfolders
- Updated documentation and example directory structure in README for clarity

## [1.2.1] - Minor update
- OUT hotfolders are now always created as siblings to the IN hotfolder, named <IN>_out
- Updated documentation and example directory structure in README for clarity

## [1.2.0] - Minor update
- OUT hotfolders are now named <IN>_out (e.g., IN = cbr_vid_s3_hotfolder, OUT = cbr_vid_s3_hotfolder_out)
- Updated documentation and example directory structure in README

## [1.1.0] - Minor update
- Production hardening: robust error handling, config validation, and never execute code from hotfolder
- Heartbeat file for process monitoring
- Auto-create OUT folders and remove them if IN is deleted and OUT is empty
- Improved .gitignore to exclude generated/state files and heartbeat
- Documented example-hotfolders structure in README and removed example-hotfolders from repo

## [1.0.0] - Initial production-ready release
- Hotfolder monitoring with per-folder config
- Logging, log rotation, and retention
- Metadata writing for images
- Configurable copy/move/retention logic
- Automatic .DS_Store cleaning
- Debug and cleaning config groups
- Robust error handling and config validation
- Heartbeat and production hardening 