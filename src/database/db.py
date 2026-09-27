from __future__ import annotations
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, first_seen TEXT NOT NULL,
 last_seen TEXT NOT NULL, interaction_count INTEGER NOT NULL DEFAULT 0,
 trust REAL NOT NULL DEFAULT 0.2, familiarity REAL NOT NULL DEFAULT 0.0,
 preferences_json TEXT NOT NULL DEFAULT '{}', topics_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS groups (
 chat_id INTEGER PRIMARY KEY, title TEXT, chat_type TEXT, first_seen TEXT NOT NULL,
 last_seen TEXT NOT NULL, message_count INTEGER NOT NULL DEFAULT 0,
 topics_json TEXT NOT NULL DEFAULT '{}', rules_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS relationships (
 user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, trust REAL NOT NULL DEFAULT 0.2,
 familiarity REAL NOT NULL DEFAULT 0.0, interaction_count INTEGER NOT NULL DEFAULT 0,
 style TEXT, PRIMARY KEY(user_id, chat_id)
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, user_id INTEGER,
 message_id INTEGER, event_type TEXT NOT NULL, text TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
 id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, owner_id TEXT NOT NULL,
 kind TEXT NOT NULL, content TEXT NOT NULL, importance REAL NOT NULL DEFAULT 0.5,
 confidence REAL NOT NULL DEFAULT 0.5, source TEXT, created_at TEXT NOT NULL,
 last_used TEXT NOT NULL, access_count INTEGER NOT NULL DEFAULT 0,
 UNIQUE(scope, owner_id, kind, content)
);
CREATE TABLE IF NOT EXISTS state (
 key TEXT PRIMARY KEY, value_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS social_groups (
 chat_id INTEGER PRIMARY KEY,
 activity REAL NOT NULL DEFAULT 0.5,
 conversation_speed REAL NOT NULL DEFAULT 0.5,
 topic TEXT NOT NULL DEFAULT '',
 engagement REAL NOT NULL DEFAULT 0.45,
 last_message_at TEXT,
 last_bot_message_at TEXT
);
CREATE TABLE IF NOT EXISTS goals (
 id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, owner_id TEXT NOT NULL,
 goal TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', priority REAL NOT NULL DEFAULT 0.5,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_chat_time ON events(chat_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_owner ON memories(scope, owner_id, importance DESC, confidence DESC);
CREATE TABLE IF NOT EXISTS attention_state (
 chat_id INTEGER PRIMARY KEY, target_user_id INTEGER, topic TEXT NOT NULL DEFAULT '',
 focus REAL NOT NULL DEFAULT 0.0, last_event_at TEXT, last_attention_at TEXT,
 turns_since_reply INTEGER NOT NULL DEFAULT 0, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS conversation_threads (
 id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, topic TEXT NOT NULL,
 started_at TEXT NOT NULL, last_event_at TEXT NOT NULL, last_user_id INTEGER,
 turns INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active', UNIQUE(chat_id, topic)
);
CREATE INDEX IF NOT EXISTS idx_threads_chat_time ON conversation_threads(chat_id, last_event_at);
CREATE INDEX IF NOT EXISTS idx_attention_chat ON attention_state(chat_id);
CREATE TABLE IF NOT EXISTS media_memories (
 id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, user_id INTEGER,
 file_id TEXT NOT NULL UNIQUE, media_type TEXT NOT NULL, caption TEXT,
 unique_id TEXT, mime_type TEXT, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_media_chat ON media_memories(chat_id, created_at);
CREATE TABLE IF NOT EXISTS presentations (
 user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, presentation TEXT NOT NULL DEFAULT 'adaptive',
 style TEXT NOT NULL DEFAULT 'natural', confidence REAL NOT NULL DEFAULT .5,
 PRIMARY KEY(user_id, chat_id)
);
CREATE TABLE IF NOT EXISTS learned_claims (
 id INTEGER PRIMARY KEY AUTOINCREMENT, subject_id INTEGER, chat_id INTEGER, claim TEXT NOT NULL,
 kind TEXT NOT NULL DEFAULT 'observation', confidence REAL NOT NULL DEFAULT .35,
 source_user_id INTEGER, status TEXT NOT NULL DEFAULT 'inferred', created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL, UNIQUE(subject_id, chat_id, claim)
);
CREATE INDEX IF NOT EXISTS idx_claim_subject ON learned_claims(subject_id, chat_id, confidence DESC);
CREATE TABLE IF NOT EXISTS self_reflections (
 id INTEGER PRIMARY KEY AUTOINCREMENT, summary TEXT NOT NULL,
 mood TEXT, social_mode TEXT, created_at REAL NOT NULL
);
"""

class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.conn:
            self.conn.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple[Any, ...] = ()):
        with self.lock, self.conn:
            cur = self.conn.execute(sql, params)
            return cur

    def query(self, sql: str, params: tuple[Any, ...] = ()):
        return self.execute(sql, params).fetchall()

    def close(self):
        with self.lock:
            self.conn.close()
