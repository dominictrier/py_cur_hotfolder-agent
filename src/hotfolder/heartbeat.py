import os
from pathlib import Path
from datetime import datetime

def write_heartbeat(heartbeat_dir="heartbeat"):
    hb_dir = Path(__file__).parent.parent / heartbeat_dir
    hb_dir.mkdir(exist_ok=True)
    hb_file = hb_dir / "heartbeat.txt"
    with open(hb_file, "w") as f:
        f.write(datetime.now().isoformat()) 