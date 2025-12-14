import sqlite3
from pathlib import Path

db_path = Path("backend/provider_directory.db")

print("DB file exists:", db_path.exists())
print("DB absolute path:", db_path.resolve())

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("\nTables:")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    print(row)

print("\nProviders:")
for row in cur.execute("SELECT id, external_id, name FROM providers;"):
    print(row)

conn.close()
