import sqlite3

conn = sqlite3.connect("manufacturing.db")
cursor = conn.cursor()

# Machines
cursor.execute("""
CREATE TABLE IF NOT EXISTS machines(
    machine_id TEXT PRIMARY KEY,
    machine_name TEXT,
    machine_type TEXT,
    location TEXT
)
""")

# Production Logs
cursor.execute("""
CREATE TABLE IF NOT EXISTS production_logs(
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    machine_id TEXT,
    planned_runtime_minutes INTEGER,
    actual_runtime_minutes INTEGER,
    downtime_minutes INTEGER,
    production_count INTEGER,
    rejection_count INTEGER,
    target_count INTEGER,
    FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
)
""")

# Downtime Logs
cursor.execute("""
CREATE TABLE IF NOT EXISTS downtime_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    machine_id TEXT,
    reason TEXT,
    downtime_minutes INTEGER,
    FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
)
""")

# Machine Alerts
cursor.execute("""
CREATE TABLE IF NOT EXISTS machine_alerts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    machine_id TEXT,
    alert_type TEXT,
    severity TEXT,
    FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
)
""")

conn.commit()
conn.close()

print("Database Created Successfully")