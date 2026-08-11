"""Probe ~/.omniroute/storage.sqlite to understand what's actually encrypted
vs plaintext, and what objects are present. Read-only, never modifies the DB.
"""
import os
import sqlite3

DB = os.path.expanduser(r"~\.omniroute\storage.sqlite")
print(f"DB path: {DB}")
print(f"DB exists: {os.path.exists(DB)}")
print(f"DB size: {os.path.getsize(DB) if os.path.exists(DB) else 'n/a'} bytes")

if not os.path.exists(DB):
    raise SystemExit("DB missing")

# Open read-only via URI to avoid touching -wal / -shm
uri = f"file:{DB}?mode=ro&immutable=1"
con = sqlite3.connect(uri, uri=True)
cur = con.cursor()

print("\n--- Tables ---")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(f"  {row[0]}")

print("\n--- Row counts ---")
for (t,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
        print(f"  {t}: {n} rows")
    except sqlite3.OperationalError as e:
        print(f"  {t}: error {e}")

print("\n--- Provider / connection sample (first 5 rows, truncated) ---")
for tbl in ("providers", "connections", "provider_connections", "oauth_accounts", "api_keys"):
    try:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info('{tbl}')").fetchall()]
        if not cols:
            continue
        print(f"\n  table {tbl}: cols={cols}")
        for r in cur.execute(f"SELECT * FROM '{tbl}' LIMIT 5").fetchall():
            row_repr = []
            for v in r:
                s = str(v)
                if len(s) > 80:
                    s = s[:77] + "..."
                row_repr.append(s)
            print(f"    {row_repr}")
    except sqlite3.OperationalError as e:
        print(f"  (no table {tbl}: {e})")

con.close()
