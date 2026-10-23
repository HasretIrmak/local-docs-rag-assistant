import sqlite3
import json
import time
from typing import List, Dict, Any, Optional
from config import DB_PATH

def init_db():
    """
    SQLite veritabanı tablolarını oluşturur.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Oturumlar (Sessions) Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            doc_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    
    # Mesajlar (Messages) Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            context_json TEXT,
            is_fallback INTEGER DEFAULT 0,
            timestamp REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def session_olustur(session_id: str, title: str, doc_name: str, model_name: str) -> Dict[str, Any]:
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (id, title, doc_name, model_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, title, doc_name, model_name, now, now))
    conn.commit()
    conn.close()
    return {
        "id": session_id,
        "title": title,
        "doc_name": doc_name,
        "model_name": model_name,
        "created_at": now,
        "updated_at": now
    }

def session_guncelle_model(session_id: str, model_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET model_name = ?, updated_at = ? WHERE id = ?", (model_name, time.time(), session_id))
    conn.commit()
    conn.close()

def session_guncelle_baslik(session_id: str, title: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, time.time(), session_id))
    conn.commit()
    conn.close()

def session_listesi_getir() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

def session_getir(session_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def session_sil(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def mesaj_ekle(session_id: str, role: str, content: str, context_json: Optional[str] = None, is_fallback: bool = False):
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (session_id, role, content, context_json, is_fallback, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, role, content, context_json, 1 if is_fallback else 0, now))
    cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()

def mesajlari_getir(session_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("context_json"):
            try:
                d["context"] = json.loads(d["context_json"])
            except Exception:
                d["context"] = None
        else:
            d["context"] = None
        result.append(d)
    conn.close()
    return result

# DB ilklendir
init_db()
