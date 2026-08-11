"""Find db_meta rows, encryption metadata. Read-only."""
import os, sqlite3
DB = os.path.expanduser(r"~\.omniroute\storage.sqlite")
uri = f"file:{DB}?mode=ro&immutable=1"
con = sqlite3.connect(uri, uri=True)
cur = con.cursor()

print("--- db_meta ---")
try:
    cols = [c[1] for c in cur.execute("PRAGMA table_info('db_meta')").fetchall()]
    print(f"cols: {cols}")
    for r in cur.execute("SELECT * FROM db_meta").fetchall():
        print(f"  {list(r)}")
except sqlite3.OperationalError as e:
    print(f"db_meta error: {e}")

print("\n--- key_value table (if exists) ---")
try:
    cols = [c[1] for c in cur.execute("PRAGMA table_info('key_value')").fetchall()]
    print(f"cols: {cols}")
    for r in cur.execute("SELECT * FROM key_value LIMIT 20").fetchall():
        row_repr = []
        for v in r:
            s = str(v)
            row_repr.append(s[:200])
        print(f"  {row_repr}")
except sqlite3.OperationalError as e:
    print(f"key_value error: {e}")

print("\n--- _omniroute_migrations (last 10) ---")
try:
    cols = [c[1] for c in cur.execute("PRAGMA table_info('_omniroute_migrations')").fetchall()]
    print(f"cols: {cols}")
    for r in cur.execute("SELECT * FROM _omniroute_migrations ORDER BY rowid DESC LIMIT 10").fetchall():
        print(f"  {list(r)}")
except sqlite3.OperationalError as e:
    print(f"_omniroute_migrations error: {e}")

con.close()
