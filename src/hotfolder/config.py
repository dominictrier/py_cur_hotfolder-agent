import json
from pathlib import Path

GLOBAL_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

# Grouped config keys and their subkeys
GROUPED_KEYS = {
    "timing": ["scan_interval", "resting_time"],
    "flattening": ["dissolve_folders"],
    "metadata": ["metadata", "metadata_field"],
    "logging": ["log_retention"],
    "buffering": ["keep_files", "ignore_updates"],
    "debugging": ["debug"],
    "mtime": ["update_mtime"]
}

REQUIRED_FIELDS = [
    "resting_time",
    "dissolve_folders",
    "metadata",
    "metadata_field",
    "log_retention",
    "scan_interval",
    "keep_files",
    "ignore_updates"
]

DEFAULT_CONFIG = {
    "resting_time": 300,
    "dissolve_folders": False,
    "metadata": False,
    "metadata_field": "",
    "log_retention": 7,
    "scan_interval": 10,
    "keep_files": False,
    "ignore_updates": False,
    "autoclean": True,
    "debug": True,
    "update_mtime": False
}

def flatten_grouped_config(config):
    # Flatten grouped config structure to flat dict for code compatibility
    flat = dict(config)
    for group, keys in GROUPED_KEYS.items():
        group_val = config.get(group, {})
        for key in keys:
            if key in group_val:
                flat[key] = group_val[key]
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
        "timing": {k: example_config[k] for k in GROUPED_KEYS["timing"]},
        "flattening": {k: example_config[k] for k in GROUPED_KEYS["flattening"]},
        "metadata": {k: example_config[k] for k in GROUPED_KEYS["metadata"]},
        "logging": {k: example_config[k] for k in GROUPED_KEYS["logging"]},
        "buffering": {k: example_config[k] for k in GROUPED_KEYS["buffering"]},
        "mtime": {k: example_config[k] for k in GROUPED_KEYS["mtime"]},
        "debugging": {k: example_config[k] for k in GROUPED_KEYS["debugging"]}
    }
    if config_file.exists():
        with open(config_file, "r") as f:
            folder_config = json.load(f)
        flat_folder = flatten_grouped_config(folder_config)
        merged = {**base, **flat_folder}
        return validate_config(merged)
    else:
        # Create example config if not present
        if not example_file.exists():
            with open(example_file, "w") as f:
                json.dump(grouped_example, f, indent=2)
        # Always use global config if no config.json is present
        return base 