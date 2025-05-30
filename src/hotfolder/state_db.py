import sqlite3
from pathlib import Path
import threading
import time

class HotfolderStateDB:
    """
    SQLite-backed state manager for hotfolder job tracking.
    Tracks seen and processed files per hotfolder, replacing .seen.json and .processed.json.
    All state is kept in .db/hotfolder_state.db in the hotfolder.
    Thread-safe for use in multi-threaded watcher.
    """
    def __init__(self, folder: Path):
        """
        Initialize the state DB for a given hotfolder.
        Creates the database and tables if they do not exist.
        """
        folder = Path(folder)
        folder.mkdir(exist_ok=True)  # Ensure hotfolder exists
        db_dir = folder / ".db"
        db_dir.mkdir(exist_ok=True)
        self.db_path = db_dir / "hotfolder_state.db"
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """
        Create tables for seen_files and processed_files if they do not exist.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS seen_files (
                file_path TEXT PRIMARY KEY,
                seen_time REAL,
                mtime REAL
            )''')

            c.execute('''CREATE TABLE IF NOT EXISTS processed_files (
                file_path TEXT PRIMARY KEY,
                processed_time REAL,
                mtime REAL,
                ready_for_deletion INTEGER DEFAULT 0
            )''')
            conn.commit()

    # --- Seen files ---

    def set_seen(self, file_path: str, seen_time: float, mtime: float):
        """
        Mark a file as seen, with its seen_time and mtime.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO seen_files (file_path, seen_time, mtime) VALUES (?, ?, ?)''',
                      (file_path, seen_time, mtime))
            conn.commit()

    def get_seen(self):
        """
        Return a dict of all seen files: {file_path: {'seen_time': ..., 'mtime': ...}}
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT file_path, seen_time, mtime FROM seen_files')
            return {row[0]: {'seen_time': row[1], 'mtime': row[2]} for row in c.fetchall()}

    def remove_seen(self, file_path: str):
        """
        Remove a file from the seen_files table.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM seen_files WHERE file_path = ?', (file_path,))
            conn.commit()

    def clear_seen(self):
        """
        Remove all entries from the seen_files table.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM seen_files')
            conn.commit()

    def remove_seen_prefix(self, prefix: str):
        """
        Remove all seen files where file_path starts with prefix or equals prefix.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM seen_files WHERE file_path = ? OR file_path LIKE ?', (prefix, f'{prefix}/%'))
            conn.commit()

    # --- Processed files ---

    def set_processed(self, file_path: str, processed_time: float, mtime: float, ready_for_deletion: bool = False):
        """
        Mark a file as processed, with its processed_time, mtime, and ready_for_deletion flag.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO processed_files (file_path, processed_time, mtime, ready_for_deletion) VALUES (?, ?, ?, ?)''',
                      (file_path, processed_time, mtime, int(ready_for_deletion)))
            conn.commit()

    def get_processed(self):
        """
        Return a dict of all processed files: {file_path: {'processed_time': ..., 'mtime': ...}}
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT file_path, processed_time, mtime FROM processed_files')
            return {row[0]: {'processed_time': row[1], 'mtime': row[2]} for row in c.fetchall()}

    def remove_processed(self, file_path: str):
        """
        Remove a file from the processed_files table.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM processed_files WHERE file_path = ?', (file_path,))
            conn.commit()

    def remove_processed_prefix(self, prefix: str):
        """
        Remove all processed files where file_path starts with prefix or equals prefix.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM processed_files WHERE file_path = ? OR file_path LIKE ?', (prefix, f'{prefix}/%'))
            conn.commit()

    def clear_processed(self):
        """
        Remove all entries from the processed_files table.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM processed_files')
            conn.commit()

    def mark_ready_for_deletion(self, job_folder: str):
        """
        Mark a job folder as ready for deletion (set ready_for_deletion=1 for the folder entry).
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''UPDATE processed_files SET ready_for_deletion=1 WHERE file_path = ?''', (job_folder,))
            conn.commit()

    def get_ready_for_deletion_jobs(self):
        """
        Return a list of job folder names marked as ready for deletion.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''SELECT file_path FROM processed_files WHERE ready_for_deletion=1''')
            return [row[0] for row in c.fetchall()]

    # --- Utility ---

    def vacuum(self):
        """
        Run VACUUM to compact the database file.
        """
        with self.lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('VACUUM')
            conn.commit() 