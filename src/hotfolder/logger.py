import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os

class OnDemandFileHandler(logging.Handler):
    def __init__(self, log_file, retention_days):
        super().__init__()
        self.log_file = log_file
        self.retention_days = retention_days
        self.inner_handler = None

    def emit(self, record):
        if self.inner_handler is None:
            log_dir = self.log_file.parent
            if not log_dir.exists():
                log_dir.mkdir(exist_ok=True)
            self.inner_handler = TimedRotatingFileHandler(
                self.log_file, when="midnight", backupCount=self.retention_days
            )
            # Ensure rotated logs use a date suffix (before extension)
            self.inner_handler.suffix = "%Y-%m-%d"
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            self.inner_handler.setFormatter(formatter)
        self.inner_handler.emit(record)

def get_hotfolder_logger(hotfolder_path, retention_days=7):
    # Special handling for global logger
    if hotfolder_path == "global":
        log_dir = Path("logs")
        log_file = log_dir / "global.log"
    else:
        hotfolder_path = Path(hotfolder_path)
        log_dir = hotfolder_path / ".log"
        log_file = log_dir / f"{hotfolder_path.name}.log"

    logger = logging.getLogger(f"hotfolder.{hotfolder_path}")
    logger.setLevel(logging.INFO)
    # Remove all handlers to avoid duplicate logs if re-instantiated
    logger.handlers = []
    handler = OnDemandFileHandler(log_file, retention_days)
    logger.addHandler(handler)
    return logger

# New: Debug logger for parallel debug log file
_own_debug_loggers = {}
def get_hotfolder_debug_logger(hotfolder_path):
    hotfolder_path = str(hotfolder_path)
    if hotfolder_path in _own_debug_loggers:
        return _own_debug_loggers[hotfolder_path]
    log_dir = Path(hotfolder_path) / ".log" if hotfolder_path != "global" else Path("logs")
    log_dir.mkdir(exist_ok=True)
    if hotfolder_path == "global":
        log_file = log_dir / "global.debug.log"
        logger_name = "global_debug"
    else:
        log_file = log_dir / f"{Path(hotfolder_path).name}.debug.log"
        logger_name = f"{Path(hotfolder_path).name}_debug"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(fh)
    _own_debug_loggers[hotfolder_path] = logger
    return logger 