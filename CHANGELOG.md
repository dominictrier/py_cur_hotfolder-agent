# Changelog

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