# Technical Requirements Document - Hotfolder System

## 1. System Overview

### 1.1 Purpose
The Hotfolder System is a Python-based file processing system designed for 24/7 unattended operation. It monitors input directories for new files/folders, processes them according to configurable rules, and moves or copies them to output directories.

### 1.2 Scope
The system provides automated file processing with support for:
- Multiple hotfolder monitoring
- Per-hotfolder configuration
- Metadata injection for image files
- Advanced file retention and copying logic
- Comprehensive logging and debugging capabilities

## 2. Technical Requirements

### 2.1 System Requirements

#### 2.1.1 Platform Requirements
- Operating System: macOS (primary) or Linux
- Python Version: 3.7 or higher
- Disk Space: Sufficient for file processing and logging
- Memory: Dependent on file processing volume

#### 2.1.2 Dependencies
Required Python packages:
- Pillow: For image processing
- iptcinfo3: For IPTC metadata manipulation
- PyYAML: For configuration file handling
- Additional dependencies as specified in requirements.txt

### 2.2 Functional Requirements

#### 2.2.1 File System Monitoring
- **Multiple Directory Support**: Monitor multiple input directories simultaneously
- **Dynamic Detection**: Automatically detect new and removed hotfolders
- **Stability Detection**: Implement configurable file stability checking
- **File System Events**: Track file modification times and changes

#### 2.2.2 File Processing
- **Copy/Move Operations**: Support both copying and moving files
- **Folder Structure**: Option to maintain or flatten folder structure
- **System File Handling**: Skip system files (.DS_Store, thumbs.db)
- **File Retention**: Configurable file retention policies
- **Modification Time**: Update file modification times after processing

#### 2.2.3 Metadata Management
- **Image File Support**: Process .jpg, .jpeg, .png, .tif, .tiff files
- **IPTC Fields**: Write metadata to configurable IPTC fields
- **Error Handling**: Continue processing if metadata operations fail

#### 2.2.4 Configuration Management
- **Global Configuration**: Support for system-wide settings
- **Per-Hotfolder Configuration**: Allow folder-specific overrides
- **Configuration Validation**: Strict type checking and validation
- **Auto-Configuration**: Generate example configurations automatically

### 2.3 Performance Requirements

#### 2.3.1 Monitoring
- **Scan Interval**: Configurable, default 10 seconds
- **Resting Time**: Configurable stability period, default 300 seconds
- **Resource Usage**: Minimal CPU and memory footprint during idle periods

#### 2.3.2 Processing
- **Concurrent Processing**: Handle multiple hotfolders simultaneously
- **Error Recovery**: Graceful handling of processing failures
- **Resource Management**: Efficient file system operations

### 2.4 Security Requirements

#### 2.4.1 File System Security
- **Permission Handling**: Respect file system permissions
- **Error Handling**: Secure handling of access errors
- **Path Validation**: Proper handling of paths with special characters

### 2.5 Logging Requirements

#### 2.5.1 Log Management
- **Per-Hotfolder Logging**: Separate log files for each hotfolder
- **Log Rotation**: Automatic log rotation with configurable retention
- **Debug Logging**: Optional detailed logging for troubleshooting
- **Log Content**: Record all actions, errors, and metadata operations

#### 2.5.2 Monitoring
- **Heartbeat System**: Optional heartbeat file generation for external monitoring
- **Status Tracking**: Track processing status in SQLite database

### 2.6 Configuration Requirements

#### 2.6.1 Global Configuration
Required configuration groups:
- Hotfolders: List of root directories to monitor
- Schedule: Scan and resting time settings
- Retention: File retention and cleanup policies
- Structure: Folder structure handling
- Metadata: Image metadata injection settings
- Auto-cleanup: System file handling
- Logging: Log management settings
- Debugging: Debug mode settings
- Heartbeat: External monitoring settings

#### 2.6.2 Per-Hotfolder Configuration
- Support all global configuration options
- Allow selective override of global settings
- Automatic generation of example configurations

## 3. Directory Structure Requirements

### 3.1 Project Structure
```
hotfolder_root/
├── IN_folder/
│   ├── .config/
│   │   ├── config.yml
│   │   └── config.yml.example
│   ├── .log/
│   │   ├── hotfolder.log
│   │   └── hotfolder.debug.log
│   └── .hotfolder_state.db
└── IN_folder_out/
```

### 3.2 State Management
- Use SQLite database for state tracking
- Maintain processing history
- Track file modifications and processing status

## 4. Error Handling Requirements

### 4.1 Error Scenarios
- File access errors
- Configuration errors
- Metadata processing errors
- File system operation errors
- Database errors

### 4.2 Error Recovery
- Graceful error handling
- Detailed error logging
- Continued operation after non-critical errors
- Automatic retry mechanisms where appropriate

## 5. Deployment Requirements

### 5.1 Installation
- Python package installation via pip
- Configuration file setup
- Directory structure creation

### 5.2 Service Management
- Support for launchd on macOS
- Proper service configuration
- Automatic restart capability

## 6. Documentation Requirements

### 6.1 Required Documentation
- Installation instructions
- Configuration guide
- Troubleshooting guide
- API documentation
- Version history

### 6.2 Code Documentation
- Function and class documentation
- Inline comments for complex logic
- Type hints for Python functions

## 7. Testing Requirements

### 7.1 Test Coverage
- Unit tests for core functionality
- Integration tests for file processing
- Configuration validation tests
- Error handling tests

### 7.2 Test Environments
- Clean environment testing
- Various file system scenarios
- Error condition testing

## 8. Maintenance Requirements

### 8.1 Version Control
- Semantic versioning
- Version tracking in source code
- Changelog maintenance

### 8.2 Updates
- Dependency updates
- Security patch management
- Backward compatibility considerations 