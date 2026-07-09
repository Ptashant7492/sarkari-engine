import sqlite3
import hashlib
from config import DB_PATH
from core.utils.logger import logger

def get_db_connection():
    """Establishes a connection to the SQLite database with explicit row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_links (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'PENDING', -- PENDING, PARSED, PUBLISHED, FAILED
                    wp_post_id INTEGER DEFAULT NULL
                )
            """)
            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.critical(f"Failed to initialize database: {e}")
        raise

def generate_hash(url: str) -> str:
    """Generates a deterministic SHA-256 hash for a URL to act as a unique key."""
    return hashlib.sha256(url.strip().lower().encode('utf-8')).hexdigest()

def is_link_processed(url: str) -> bool:
    """Checks if a URL has already been captured by the system."""
    url_hash = generate_hash(url)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM scraped_links WHERE url_hash = ?", (url_hash,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Error checking link existence for {url}: {e}")
        return False # Fail-safe: assume false but log error to prevent pipeline crash

def log_new_link(url: str, source: str) -> bool:
    """Inserts a new link into the system. Returns True if inserted, False if skipped."""
    if is_link_processed(url):
        return False
        
    url_hash = generate_hash(url)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scraped_links (url_hash, url, source) VALUES (?, ?, ?)",
                (url_hash, url, source)
            )
            conn.commit()
            logger.info(f"🆕 Link tracked safely: {url} [{source}]")
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to log link {url}: {e}")
        return False
