import os
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Redis Setup (Dynamic fallback)
redis_client = None
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2.0)
        redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis at {REDIS_URL}, falling back to SQLite: {e}")
        redis_client = None

# SQLite setup
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Analysis runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        resume_name TEXT,
        match_score REAL,
        keyword_score REAL,
        semantic_score REAL,
        details TEXT
    )
    """)
    
    # 2. Telemetry logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        provider TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cost REAL,
        latency REAL,
        status TEXT
    )
    """)
    
    # 3. Fine-tuning dataset
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS finetuning_dataset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        instruction TEXT,
        input TEXT,
        output TEXT
    )
    """)
    
    # 4. Jobs Cache
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs_cache (
        id TEXT PRIMARY KEY,
        title TEXT,
        company TEXT,
        location TEXT,
        description TEXT,
        url TEXT,
        salary TEXT,
        source TEXT,
        posted_date TEXT,
        job_type TEXT,
        tags TEXT,
        remote INTEGER
    )
    """)
    
    # 5. Sessions/Payment
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_sessions (
        session_id TEXT PRIMARY KEY,
        timestamp TEXT,
        cardholder TEXT,
        amount REAL,
        status TEXT
    )
    """)
    
    # 6. Key-Value Cache Table for fallback
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kv_cache (
        key TEXT PRIMARY KEY,
        value TEXT,
        expires_at REAL
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# Cache helpers with Redis fallback
def set_cache(key: str, value: Any, expire_seconds: int = 3600):
    if redis_client:
        try:
            redis_client.setex(key, expire_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")
    
    # SQLite Cache Fallback
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        expires_at = datetime.now(timezone.utc).timestamp() + expire_seconds
        cursor.execute(
            "INSERT OR REPLACE INTO kv_cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), expires_at)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"SQLite cache set failed for {key}: {e}")
        return False

def get_cache(key: str) -> Optional[Any]:
    if redis_client:
        try:
            val = redis_client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
            
    # SQLite Cache Fallback
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value, expires_at FROM kv_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            value, expires_at = row[0], float(row[1])
            if expires_at > datetime.now(timezone.utc).timestamp():
                return json.loads(value)
            else:
                # Clean up expired
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM kv_cache WHERE key = ?", (key,))
                conn.commit()
                conn.close()
        return None
    except Exception as e:
        logger.error(f"SQLite cache get failed for {key}: {e}")
        return None

