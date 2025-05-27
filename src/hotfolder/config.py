import json
from pathlib import Path

GLOBAL_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

# Grouped config keys and their subkeys
GROUPED_KEYS = {
    "schedule": ["scan_interval", "resting_time", "retention_cleanup_time"],
    "retention": ["keep_copy", "ignore_updates"],
    "structure": ["dissolve_folders"],
    "metadata": ["metadata", "metadata_field"],
    "logging": ["log_retention"],
    "auto_cleanup": ["ds_store", "retention", "thumbs_db"],
    "mtime": ["update_mtime"],
    "debugging": ["debug"]
}

REQUIRED_FIELDS = [
    "scan_interval",
    "resting_time",
    "retention_cleanup_time",
    "keep_copy",
    "ignore_updates",
    "dissolve_folders",
    "metadata",
    "metadata_field",
    "log_retention",
    "ds_store",
    "retention",
    "update_mtime",
    "debug",
    "thumbs_db"
]

DEFAULT_CONFIG = {
    "scan_interval": 10,
    "resting_time": 300,
    "retention_cleanup_time": 1440,
    "keep_copy": False,
    "ignore_updates": False,
    "dissolve_folders": False,
    "metadata": False,
    "metadata_field": "",
    "log_retention": 7,
    "ds_store": True,
    "retention": False,
    "update_mtime": True,
    "debug": False,
    "thumbs_db": True
}

def flatten_grouped_config(config):
    # Flatten grouped config structure to flat dict for code compatibility
    flat = dict(config)
    for group, keys in GROUPED_KEYS.items():
        group_val = config.get(group, {})
        for key in keys:
            if key in group_val:
                flat[key] = group_val[key]
    # Flatten auto_cleanup group
    if "auto_cleanup" in config:
        flat["ds_store"] = config["auto_cleanup"].get("ds_store", True)
        flat["retention"] = config["auto_cleanup"].get("retention", False)
        flat["thumbs_db"] = config["auto_cleanup"].get("thumbs_db", True)
    # Flatten debugging group
    if "debugging" in config:
        flat["debug"] = config["debugging"].get("debug", True)
    # Flatten mtime group
    if "mtime" in config:
        flat["update_mtime"] = config["mtime"].get("update_mtime", False)
    return flat

def validate_config(config):
    missing = [k for k in REQUIRED_FIELDS if k not in config]
    if missing:
        raise ValueError(f"Missing required config fields: {missing}")
    return config

def load_global_config():
    if GLOBAL_CONFIG_PATH.exists():
        with open(GLOBAL_CONFIG_PATH, "r") as f:
            config = json.load(f)
        flat = flatten_grouped_config(config)
        return flat
    return DEFAULT_CONFIG

def get_effective_config(hotfolder_path, global_config=None):
    from hotfolder.logger import get_hotfolder_logger
    hotfolder_path = Path(hotfolder_path)
    config_dir = hotfolder_path / ".config"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.json"
    example_file = config_dir / "config.json.example"
    # Remove hotfolders key when merging for per-folder config
    base = dict(global_config or load_global_config())
    base.pop("hotfolders", None)
    # Ensure all default fields are present in the example
    example_config = {**DEFAULT_CONFIG, **base}
    # Regroup for example file
    grouped_example = {
        "schedule": {k: example_config[k] for k in GROUPED_KEYS["schedule"]},
        "retention": {k: example_config[k] for k in GROUPED_KEYS["retention"]},
        "structure": {k: example_config[k] for k in GROUPED_KEYS["structure"]},
        "metadata": {k: example_config[k] for k in GROUPED_KEYS["metadata"]},
        "logging": {k: example_config[k] for k in GROUPED_KEYS["logging"]},
        "auto_cleanup": {k: example_config[k] for k in GROUPED_KEYS["auto_cleanup"]},
        "mtime": {k: example_config[k] for k in GROUPED_KEYS["mtime"]},
        "debugging": {k: example_config[k] for k in GROUPED_KEYS["debugging"]}
    }
    if config_file.exists():
        with open(config_file, "r") as f:
            folder_config = json.load(f)
        flat_folder = flatten_grouped_config(folder_config)
        logger = get_hotfolder_logger(hotfolder_path)
        # Strict validation: fail if any required key is missing or invalid
        for key in REQUIRED_FIELDS:
            if key not in flat_folder:
                logger.error(f"[CONFIG ERROR] Missing required key '{key}' in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
                raise ValueError(f"Missing required key '{key}' in per-hotfolder config for {hotfolder_path}")
        # Type and value checks
        type_checks = {
            "scan_interval": int,
            "resting_time": int,
            "retention_cleanup_time": int,
            "keep_copy": bool,
            "ignore_updates": bool,
            "dissolve_folders": bool,
            "metadata": bool,
            "metadata_field": str,
            "log_retention": int,
            "ds_store": bool,
            "retention": bool,
            "update_mtime": bool,
            "debug": bool,
            "thumbs_db": bool
        }
        for key, expected_type in type_checks.items():
            val = flat_folder[key]
            if not isinstance(val, expected_type):
                logger.error(f"[CONFIG ERROR] Key '{key}' in per-hotfolder config for {hotfolder_path} has wrong type: expected {expected_type.__name__}, got {type(val).__name__}. Failing hotfolder processing.")
                raise ValueError(f"Key '{key}' in per-hotfolder config for {hotfolder_path} has wrong type: expected {expected_type.__name__}, got {type(val).__name__}")
        # Value checks (e.g., positive ints)
        if flat_folder["scan_interval"] <= 0:
            logger.error(f"[CONFIG ERROR] scan_interval must be > 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"scan_interval must be > 0 in per-hotfolder config for {hotfolder_path}")
        if flat_folder["resting_time"] < 0:
            logger.error(f"[CONFIG ERROR] resting_time must be >= 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"resting_time must be >= 0 in per-hotfolder config for {hotfolder_path}")
        if flat_folder["retention_cleanup_time"] < 0:
            logger.error(f"[CONFIG ERROR] retention_cleanup_time must be >= 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"retention_cleanup_time must be >= 0 in per-hotfolder config for {hotfolder_path}")
        if flat_folder["log_retention"] < 0:
            logger.error(f"[CONFIG ERROR] log_retention must be >= 0 in per-hotfolder config for {hotfolder_path}. Failing hotfolder processing.")
            raise ValueError(f"log_retention must be >= 0 in per-hotfolder config for {hotfolder_path}")
        return flat_folder
    else:
        # Create example config if not present
        if not example_file.exists():
            with open(example_file, "w") as f:
                json.dump(grouped_example, f, indent=2)
        # Always use global config if no config.json is present
        return base 