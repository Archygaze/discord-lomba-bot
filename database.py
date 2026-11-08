import sqlite3
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = "lomba_history.db"

def set_db_path(path: str) -> None:
    """Updates the active database path."""
    global DB_PATH
    DB_PATH = path

def init_db(db_path: str = None) -> None:
    """Initializes the SQLite database and creates necessary tables."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_posts (
            post_id TEXT PRIMARY KEY,
            account TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

def is_post_seen(post_id: str, db_path: str = None) -> bool:
    """Checks whether a post ID has already been recorded."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_post_seen(post_id: str, account: str, url: str, title: str, db_path: str = None) -> None:
    """Records a post as seen in the database."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO seen_posts (post_id, account, url, title, detected_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_id, account, url, title, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def get_recent_posts(limit: int = 5, db_path: str = None) -> List[Dict[str, Any]]:
    """Returns the most recently recorded competition posts."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT post_id, account, url, title, detected_at
        FROM seen_posts
        ORDER BY detected_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_total_posts_count(db_path: str = None) -> int:
    """Returns total count of tracked posts."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM seen_posts")
    count = cursor.fetchone()[0]
    conn.close()
    return count
