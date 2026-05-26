import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database')
DB_PATH = os.path.join(DB_DIR, 'reels.db')

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            seo_title TEXT,
            description TEXT,
            hashtags TEXT,
            upload_time DATETIME,
            facebook_url TEXT,
            status TEXT DEFAULT 'pending',
            file_hash TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def is_duplicate(filename, file_hash=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if file_hash:
        cursor.execute('SELECT 1 FROM reels WHERE filename = ? OR file_hash = ?', (filename, file_hash))
    else:
        cursor.execute('SELECT 1 FROM reels WHERE filename = ?', (filename,))
        
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_reel(filename, file_hash=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO reels (filename, file_hash, status)
            VALUES (?, ?, 'pending')
        ''', (filename, file_hash))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def update_reel_metadata(filename, seo_title, description, hashtags):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reels 
        SET seo_title = ?, description = ?, hashtags = ?
        WHERE filename = ?
    ''', (seo_title, description, hashtags, filename))
    conn.commit()
    conn.close()

def mark_reel_uploaded(filename, facebook_url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reels 
        SET status = 'uploaded', facebook_url = ?, upload_time = ?
        WHERE filename = ?
    ''', (facebook_url, datetime.now().isoformat(), filename))
    conn.commit()
    conn.close()

def mark_reel_failed(filename):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reels 
        SET status = 'failed'
        WHERE filename = ?
    ''', (filename,))
    conn.commit()
    conn.close()

def get_daily_upload_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM reels 
        WHERE status = 'uploaded' AND date(upload_time) = ?
    ''', (today,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

init_db()
