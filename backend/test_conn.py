# salva como test_conn.py ou roda no REPL
from database import get_conn, USE_MEMORY_DB
print("USE_MEMORY_DB=", USE_MEMORY_DB)
conn = get_conn()
print("conn:", conn)
if conn:
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(cur.fetchone())
    conn.close()
