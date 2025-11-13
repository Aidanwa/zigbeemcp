from __future__ import annotations
import os, sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./data/smarthome.sqlite3"))

DDL = """
CREATE TABLE IF NOT EXISTS lightevents (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now')),
  device TEXT NOT NULL,
  source TEXT NOT NULL,
  state TEXT,
  brightness INTEGER,
  color_temp INTEGER,
  payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_device_ts ON lightevents(device, ts DESC);
-- optional if you often run global time-range scans:
-- CREATE INDEX IF NOT EXISTS idx_ts ON lightevents(ts);
"""

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.executescript(DDL)
    return conn
