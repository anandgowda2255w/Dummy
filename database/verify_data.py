import sqlite3

conn = sqlite3.connect("manufacturing.db")
cursor = conn.cursor()

tables = [
    "machines",
    "production_logs",
    "downtime_logs",
    "machine_alerts"
]

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table}: {count}")

conn.close()