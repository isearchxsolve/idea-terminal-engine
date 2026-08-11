"""Find any row that mentions encryption, schema_version, or storage key.
Read-only. Scan db_meta and key_value namespaces exhaustively."""
import os, sqlite3
DB = os.path.expanduser(r"~\.omniroute\storage.sqlite")
uri = f"file:{DB}?mode=ro&immutable=1"
con = sqlite3.connect(uri, uri=True)
cur = con.cursor()

patterns = ("encrypt", "key", "cipher", "schema_version", "storage_key",
            "masterKey", "version")

print("--- db_meta ALL rows ---")
try:
    for r in cur.execute("SELECT * FROM db_meta").fetchall():
        print(f"  db_meta: {list(r)}")
except Exception as e:
    print(f"db_meta error: {e}")

print("\n--- key_value ALL rows that match patterns ---")
try:
    for row in cur.execute(
        "SELECT namespace, key, value FROM key_value "
        "WHERE namespace LIKE '%' OR key LIKE '%encrypt%' OR key LIKE '%key%' "
        "OR key LIKE '%cipher%' OR value LIKE '%encrypt%' "
        "OR value LIKE '%cipher%'"
    ).fetchall():
        v = str(row[2])
        if len(v) > 200:
            v = v[:200] + "..."
        print(f"  [{row[0]}/{row[1]}] = {v}")
except Exception as e:
    print(f"key_value error: {e}")

print("\n--- searching ALL tables for any column containing the literal token 'enc:' prefix (encryption marker) ---")
print("(this would tell us if ANY value actually appears encrypted)")
tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()]
suspicious = 0
for t in tables:
    try:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info('{t}')").fetchall()]
        for col in cols:
            try:
                # Look for very common encryption prefixes OmniRoute might use
                rows = cur.execute(
                    f"SELECT COUNT(*) FROM '{t}' WHERE \"{col}\" LIKE 'enc:%' OR \"{col}\" LIKE 'v1:%'"
                ).fetchone()[0]
                if rows > 0:
                    print(f"  ENCRYPTED-LIKE values: {t}.{col} = {rows} rows")
                    suspicious += rows
            except sqlite3.OperationalError:
                pass
    except sqlite3.OperationalError:
        pass
print(f"\nTotal rows with enc:/v1: prefix (likely encrypted): {suspicious}")

# Also show audit_log entries from the moment OmniRoute last tried to start
print("\n--- audit_log last 20 (newest last) ---")
try:
    cols = [c[1] for c in cur.execute("PRAGMA table_info('audit_log')").fetchall()]
    print(f"audit_log cols: {cols}")
    # find the timestamp column
    ts_col = next((c for c in cols if 'time' in c.lower() or 'at' in c.lower()), cols[0] if cols else None)
    if ts_col:
        for r in cur.execute(
            f"SELECT * FROM audit_log ORDER BY \"{ts_col}\" DESC LIMIT 20"
        ).fetchall():
            row_repr = []
            for v in r:
                s = str(v)
                row_repr.append(s[:120])
            print(f"  {row_repr}")
except Exception as e:
    print(f"audit_log error: {e}")

con.close()
