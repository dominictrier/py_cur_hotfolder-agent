import yaml
from pathlib import Path
import os
from collections import OrderedDict

group_comments = OrderedDict([
    ("hotfolders", "# === Hotfolder Roots ==="),
    ("schedule", "# === Schedule Settings ==="),
    ("retention", "# === Retention Policy ==="),
    ("structure", "# === Folder Structure ==="),
    ("metadata", "# === Metadata Handling ==="),
    ("auto_cleanup", "# === Auto Cleanup Options ==="),
    ("mtime", "# === File Modification Time Handling ==="),
    ("logging", "# === Logging Settings ==="),
    ("debugging", "# === Debugging ==="),
])
key_comments = {
    "scan_interval": "# Seconds between scans of the hotfolder",
    "resting_time": "# Seconds a job must be unchanged before processing",
    "cleanup": "# Perform retention cleanup after jobs are processed",
    "keep_copy": "# Keep a copy of jobs in IN after processing",
    "cleanup_time": "# Minutes to keep jobs in IN after processing",
    "dissolve_folders": "# If true, flatten job folders when moving to OUT",
    "enabled": "# Enable/disable metadata extraction",
    "field": "# Optional: specify a metadata field to extract",
    "ds_store": "# Remove .DS_Store files from jobs",
    "thumbs_db": "# Remove Thumbs.db files from jobs",
    "update_mtime": "# Update mtime on files after processing",
    "log_retention": "# Days to keep log files",
    "debug": "# Enable debug logging",
}

GLOBAL_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yml"

GROUPED_KEYS = OrderedDict([
    ("hotfolders", []),
    ("schedule", ["scan_interval", "resting_time"]),
    ("retention", ["keep_copy", "cleanup", "cleanup_time"]),
    ("structure", ["dissolve_folders"]),
    ("metadata", ["inject_folder_name", "metadata_field"]),
    ("auto_cleanup", ["ds_store", "thumbs_db"]),
    ("mtime", ["update_mtime"]),
    ("logging", ["log_retention"]),
    ("debugging", ["debug"]),
])

REQUIRED_FIELDS = [
    "scan_interval",
    "resting_time",
    "cleanup",           # retention.cleanup
    "keep_copy",         # retention.keep_copy
    "cleanup_time",      # retention.cleanup_time
    "dissolve_folders",
    "inject_folder_name",
    "metadata_field",
    "log_retention",
    "ds_store",
    "update_mtime",
    "debug",
    "thumbs_db"
]

DEFAULT_CONFIG = {
    "hotfolders": [],
    "scan_interval": 10,
    "resting_time": 300,
    "cleanup": True,
    "keep_copy": False,
    "cleanup_time": 1440,
    "dissolve_folders": False,
    "inject_folder_name": False,
    "metadata_field": "headline",
    "log_retention": 7,
    "ds_store": True,
    "update_mtime": True,
    "debug": False,
    "thumbs_db": True
}

def flatten_grouped_config(config):
    flat = dict(config)
    for group, keys in GROUPED_KEYS.items():
        group_val = config.get(group, {})
        if group == "metadata":
            flat["inject_folder_name"] = group_val.get("inject_folder_name", False)
            flat["metadata_field"] = group_val.get("metadata_field", "headline")
        elif group == "hotfolders":
            if "hotfolders" in config:
                flat["hotfolders"] = config["hotfolders"]
        else:
            for key in keys:
                if key in group_val:
                    flat[key] = group_val[key]
    if "auto_cleanup" in config:
        flat["ds_store"] = config["auto_cleanup"].get("ds_store", True)
        flat["thumbs_db"] = config["auto_cleanup"].get("thumbs_db", True)
    if "debugging" in config:
        flat["debug"] = config["debugging"].get("debug", True)
    if "mtime" in config:
        flat["update_mtime"] = config["mtime"].get("update_mtime", False)
    if "retention" in config:
        flat["cleanup"] = config["retention"].get("cleanup", True)
        flat["keep_copy"] = config["retention"].get("keep_copy", False)
        flat["cleanup_time"] = config["retention"].get("cleanup_time", 1440)
    return flat

def validate_config(config):
    missing = [k for k in REQUIRED_FIELDS if k not in config]
    if missing:
        raise ValueError(f"Missing required config fields: {missing}")
    return config

def load_global_config():
    if GLOBAL_CONFIG_PATH.exists():
        with open(GLOBAL_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        flat = flatten_grouped_config(config)
        return flat
    return DEFAULT_CONFIG

def generate_example_config_dict(include_hotfolders=True, example_config=None):
    # Returns an OrderedDict for the example config, with or without hotfolders
    if example_config is None:
        example_config = DEFAULT_CONFIG
    grouped_example = OrderedDict()
    for group in list(GROUPED_KEYS.keys()):
        if group == "hotfolders" and not include_hotfolders:
            continue
        if group == "hotfolders":
            grouped_example[group] = example_config.get("hotfolders", [])
        elif group == "metadata":
            grouped_example[group] = {
                "inject_folder_name": example_config["inject_folder_name"],
                "metadata_field": example_config["metadata_field"]
            }
        else:
            grouped_example[group] = {k: example_config[k] for k in GROUPED_KEYS[group]}
    return grouped_example

def dump_with_comments(data):
    lines = []
    for group, group_val in data.items():
        if group in group_comments:
            lines.append(group_comments[group])
        if isinstance(group_val, dict):
            lines.append(f"{group}:")
            for key, value in group_val.items():
                comment = key_comments.get(key, "")
                if comment:
                    lines.append(f"  {key}: {value} {comment}")
                else:
                    lines.append(f"  {key}: {value}")
        else:
            lines.append(f"{group}: {group_val}")
        lines.append("")
    return "\n".join(lines)

def dump_with_headlines_no_comments(data):
    lines = []
    for group, group_val in data.items():
        if group in group_comments:
            lines.append(group_comments[group])
        if isinstance(group_val, dict):
            lines.append(f"{group}:")
            for key, value in group_val.items():
                # Dump value as YAML, but without comments
                # Use yaml.safe_dump for correct formatting and lower-case booleans
                if value == "":
                    lines.append(f"  {key}: \"\"")
                else:
                    dumped = yaml.safe_dump({key: value}, default_flow_style=False, indent=2, sort_keys=False).strip()
                    dumped_lines = dumped.splitlines()
                    if len(dumped_lines) > 1:
                        lines.extend([l for l in dumped_lines[1:]])
                    else:
                        lines.append(f"  {key}: {str(value).lower() if isinstance(value, bool) else value}")
        else:
            lines.append(f"{group}: {group_val}")
        lines.append("")
    return "\n".join(lines)

def get_effective_config(hotfolder_path, global_config=None):
    from hotfolder.logger import get_hotfolder_logger
    hotfolder_path = Path(hotfolder_path)
    config_dir = hotfolder_path / ".config"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.yml"
    example_file = config_dir / "config.yml.example"
    base = dict(global_config or load_global_config())
    base.pop("hotfolders", None)
    example_config = {**DEFAULT_CONFIG, **base}
    # Per-hotfolder config example: no hotfolders group, with comments
    grouped_example = generate_example_config_dict(include_hotfolders=False, example_config=example_config)
    if config_file.exists():
        with open(config_file, "r") as f:
            folder_config = yaml.safe_load(f)
        flat_folder = flatten_grouped_config(folder_config)
        logger = get_hotfolder_logger(hotfolder_path)
        for key in REQUIRED_FIELDS:
            if key not in flat_folder:
                logger.error(f"[CONFIG ERROR] Missing required key '{key}' in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
                raise ValueError(f"Missing required key '{key}' in per-hotfolder config for {hotfolder_path}")
        type_checks = {
            "scan_interval": int,
            "resting_time": int,
            "cleanup": bool,
            "keep_copy": bool,
            "cleanup_time": int,
            "dissolve_folders": bool,
            "inject_folder_name": bool,
            "metadata_field": str,
            "log_retention": int,
            "ds_store": bool,
            "update_mtime": bool,
            "debug": bool,
            "thumbs_db": bool
        }
        for key, expected_type in type_checks.items():
            val = flat_folder[key]
            if not isinstance(val, expected_type):
                logger.error(f"[CONFIG ERROR] Key '{key}' in per-hotfolder config for {hotfolder_path} has wrong type: expected {expected_type.__name__}, got {type(val).__name__}. Failing hotfolder processing.")
                raise ValueError(f"Key '{key}' in per-hotfolder config for {hotfolder_path} has wrong type: expected {expected_type.__name__}, got {type(val).__name__}")
        if flat_folder["scan_interval"] <= 0:
            logger.error(f"[CONFIG ERROR] scan_interval must be > 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"scan_interval must be > 0 in per-hotfolder config for {hotfolder_path}")
        if flat_folder["resting_time"] < 0:
            logger.error(f"[CONFIG ERROR] resting_time must be >= 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"resting_time must be >= 0 in per-hotfolder config for {hotfolder_path}")
        if flat_folder["cleanup_time"] < 0:
            logger.error(f"[CONFIG ERROR] cleanup_time must be >= 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"cleanup_time must be >= 0 in per-hotfolder config for {hotfolder_path}")
        if flat_folder["log_retention"] < 0:
            logger.error(f"[CONFIG ERROR] log_retention must be >= 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"log_retention must be >= 0 in per-hotfolder config for {hotfolder_path}")
        return flat_folder
    else:
        if not example_file.exists():
            with open(example_file, "w") as f:
                # Write example config with headlines and empty lines, but no inline comments
                f.write(dump_with_headlines_no_comments(grouped_example))
        return base 