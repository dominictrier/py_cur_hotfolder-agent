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
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            self.inner_handler.setFormatter(formatter)
        self.inner_handler.emit(record)

def get_hotfolder_logger(hotfolder_path, retention_days=7):
    hotfolder_path = Path(hotfolder_path)
    log_dir = hotfolder_path / ".log"
    log_file = log_dir / f"{hotfolder_path.name}.log"

    logger = logging.getLogger(f"hotfolder.{hotfolder_path.name}")
    logger.setLevel(logging.INFO)
    # Remove all handlers to avoid duplicate logs if re-instantiated
    logger.handlers = []
    handler = OnDemandFileHandler(log_file, retention_days)
    logger.addHandler(handler)
    return logger 