# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.2] - 2024-06-12

### Fixed
- Fixed folder processing logic to ensure ALL files must rest before processing
- Added cleanup of both seen and processed database entries when folders are removed from IN
- Improved debug logging for file resting status
- Clarified separation between seen_time (for resting) and mtime (for changes)

## [1.10.1] - 2024-06-12

### Fixed
- Fixed mtime comparison logic to reset seen_time on any mtime change
- Improved handling of file mtime changes
- Enhanced stability of resting timer reset logic

## [1.10.0] - 2024-06-11

### Added
- Improved watcher stability with better handling of mtime changes
- Added parallel job processing support
- Enhanced debug logging for mtime changes and job state

### Changed
- Modified resting timer reset logic to be more robust
- Updated job-scoped state management
- Improved handling of file modifications

### Fixed
- Fixed incorrect removal of 'seen' state for jobs
- Improved handling of file mtime changes
- Enhanced stability of resting timer reset logic

## [1.9.2] - 2024-06-10
### Fixed
- Fixed issue where jobs were getting stuck due to incorrect mtime handling
- Improved stability of the resting timer by resetting on any mtime change
- Enhanced debug logging for mtime changes

## [1.9.1] - 2024-06-09
### Fixed
- Fixed issue where jobs were getting stuck due to incorrect mtime handling
- Improved stability of the resting timer by resetting on any mtime change
- Enhanced debug logging for mtime changes

## [1.9.0] - 2024-06-08
### Added
- Added support for per-hotfolder configuration
- Added new configuration options for metadata handling
- Added improved logging with retention policy

### Changed
- Restructured configuration to use grouped settings
- Enhanced metadata handling with configurable fields
- Improved logging system with configurable retention

### Fixed
- Fixed issue with metadata injection in certain cases
- Improved error handling in metadata operations
- Enhanced stability of the logging system

## [1.8.0] - 2024-06-07
### Added
- Added support for metadata injection into images
- Added new configuration options for metadata handling
- Added improved logging for metadata operations

### Changed
- Enhanced metadata handling with more robust error checking
- Improved logging of metadata operations
- Updated configuration structure for metadata settings

### Fixed
- Fixed issue with metadata injection in certain cases
- Improved error handling in metadata operations
- Enhanced stability of the metadata system

## [1.7.0] - 2024-06-06
### Added
- Added support for dissolving folders during move
- Added new configuration options for folder structure
- Added improved logging for folder operations

### Changed
- Enhanced folder handling with more robust error checking
- Improved logging of folder operations
- Updated configuration structure for folder settings

### Fixed
- Fixed issue with folder dissolution in certain cases
- Improved error handling in folder operations
- Enhanced stability of the folder system

## [1.6.0] - 2024-06-05
### Added
- Added support for keeping copies of processed files
- Added new configuration options for file retention
- Added improved logging for file operations

### Changed
- Enhanced file handling with more robust error checking
- Improved logging of file operations
- Updated configuration structure for file settings

### Fixed
- Fixed issue with file retention in certain cases
- Improved error handling in file operations
- Enhanced stability of the file system

## [1.5.0] - 2024-06-04
### Added
- Added support for multiple hotfolder roots
- Added new configuration options for root management
- Added improved logging for root operations

### Changed
- Enhanced root handling with more robust error checking
- Improved logging of root operations
- Updated configuration structure for root settings

### Fixed
- Fixed issue with root management in certain cases
- Improved error handling in root operations
- Enhanced stability of the root system

## [1.4.0] - 2024-06-03
### Added
- Added support for system file cleanup
- Added new configuration options for cleanup
- Added improved logging for cleanup operations

### Changed
- Enhanced cleanup with more robust error checking
- Improved logging of cleanup operations
- Updated configuration structure for cleanup settings

### Fixed
- Fixed issue with cleanup in certain cases
- Improved error handling in cleanup operations
- Enhanced stability of the cleanup system

## [1.3.0] - 2024-06-02
### Added
- Added support for file modification time handling
- Added new configuration options for mtime
- Added improved logging for mtime operations

### Changed
- Enhanced mtime handling with more robust error checking
- Improved logging of mtime operations
- Updated configuration structure for mtime settings

### Fixed
- Fixed issue with mtime handling in certain cases
- Improved error handling in mtime operations
- Enhanced stability of the mtime system

## [1.2.0] - 2024-06-01
### Added
- Added support for heartbeat monitoring
- Added new configuration options for heartbeat
- Added improved logging for heartbeat operations

### Changed
- Enhanced heartbeat with more robust error checking
- Improved logging of heartbeat operations
- Updated configuration structure for heartbeat settings

### Fixed
- Fixed issue with heartbeat in certain cases
- Improved error handling in heartbeat operations
- Enhanced stability of the heartbeat system

## [1.1.0] - 2024-05-31
### Added
- Added support for debug logging
- Added new configuration options for debugging
- Added improved logging for debug operations

### Changed
- Enhanced debug logging with more robust error checking
- Improved logging of debug operations
- Updated configuration structure for debug settings

### Fixed
- Fixed issue with debug logging in certain cases
- Improved error handling in debug operations
- Enhanced stability of the debug system

## [1.0.0] - 2024-05-30
### Added
- Initial release of the hotfolder agent
- Basic hotfolder monitoring and file processing
- Configuration system with YAML support
- Logging system with rotation
- File movement and copying capabilities
- Support for multiple hotfolder roots
- System file cleanup (.DS_Store, Thumbs.db)
- File modification time handling
- Debug logging
- Heartbeat monitoring
- Retention policy
- Folder structure options
- Metadata handling 