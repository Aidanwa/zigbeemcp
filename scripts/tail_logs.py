#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

# resolve database path
DB_PATH = Path(os.getenv("DB_PATH", "./data/smarthome.sqlite3")).expanduser()

def main():
    if not DB_PATH.exists():
        print(f"[!] database not found at {DB_PATH}")
        return

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """
        SELECT ts, device, source, state, brightness, color_temp
        FROM lightevents
        ORDER BY ts DESC
        LIMIT 10
        """
    ).fetchall()
    con.close()

    if not rows:
        print("(no events logged yet)")
        return

    print(f"\nLast {len(rows)} events from {DB_PATH}:\n" + "-" * 60)
    for r in rows:
        print(
            f"{r['ts']:<22} {r['device']:<20} "
            f"{r['state'] or '—':<6} "
            f"bri={r['brightness'] or 0:<3} "
            f"ct={r['color_temp'] or 0}"
        )

if __name__ == "__main__":
    main()
