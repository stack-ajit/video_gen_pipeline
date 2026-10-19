import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict
import json

from config.config import BASE_DIR

logger = logging.getLogger(__name__)

DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "pipeline.db"

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE,
                    title TEXT,
                    description TEXT,
                    tags TEXT,
                    video_path TEXT,
                    duration REAL,
                    youtube_status TEXT DEFAULT 'PENDING',
                    instagram_status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_topic_processed(self, topic: str) -> bool:
        """Checks if a topic has already been processed to prevent duplicates."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM videos WHERE LOWER(topic) = LOWER(?)", (topic.strip(),))
            return cursor.fetchone() is not None

    def save_video_record(
        self,
        topic: str,
        title: str,
        description: str,
        tags: List[str],
        video_path: Path,
        duration: float
    ) -> int:
        """Stores a generated video record in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO videos 
                (topic, title, description, tags, video_path, duration, youtube_status, instagram_status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 'PENDING')
            """, (
                topic.strip(),
                title,
                description,
                json.dumps(tags),
                str(video_path),
                duration
            ))
            conn.commit()
            return cursor.lastrowid

    def update_status(self, video_id: int, platform: str, status: str):
        """Updates upload status ('UPLOADED', 'FAILED', 'PENDING')."""
        column = "youtube_status" if platform.lower() == "youtube" else "instagram_status"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE videos SET {column} = ? WHERE id = ?", (status, video_id))
            conn.commit()

    def get_recent_videos(self, limit: int = 10) -> List[Dict]:
        """Returns the most recent video records."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    db = Database()
    print(f"Database initialized at {db.db_path}")
    print("Recent videos:", db.get_recent_videos(5))
