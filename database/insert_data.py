import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("manufacturing.db")
cursor = conn.cursor()

# ==================================================
# INSERT MACHINES
# ==================================================

machines = [
    ("M001", "CNC Machine 1", "CNC", "Line A"),
    ("M002", "CNC Machine 2", "CNC", "Line A"),
    ("M003", "Lathe Machine 1", "Lathe", "Line B"),
    ("M004", "Lathe Machine 2", "Lathe", "Line B"),
    ("M005", "Drill Machine 1", "Drill", "Line C"),
    ("M006", "Drill Machine 2", "Drill", "Line C"),
    ("M007", "Milling Machine 1", "Milling", "Line D"),
    ("M008", "Grinding Machine 1", "Grinding", "Line D"),
    ("M009", "Press Machine 1", "Press", "Line E"),
    ("M010", "Assembly Machine 1", "Assembly", "Line E")
]

cursor.executemany("""
INSERT INTO machines (
    machine_id,
    machine_name,
    machine_type,
    location
)
VALUES (?, ?, ?, ?)
""", machines)

# ==================================================
# TARGET COUNTS
# ==================================================

targets = {
    "M001": 1000,
    "M002": 1050,
    "M003": 900,
    "M004": 950,
    "M005": 1100,
    "M006": 980,
    "M007": 1200,
    "M008": 850,
    "M009": 1300,
    "M010": 1400
}

# ==================================================
# PRODUCTION LOGS (60 DAYS)
# ==================================================

start_date = datetime(2026, 4, 1)

for day in range(60):

    current_date = (
        start_date + timedelta(days=day)
    ).strftime("%Y-%m-%d")

    for machine_id in targets:

        planned_runtime = 480

        downtime = random.randint(20, 120)

        actual_runtime = planned_runtime - downtime

        target_count = targets[machine_id]

        production_count = random.randint(
            int(target_count * 0.80),
            target_count
        )

        rejection_count = random.randint(
            5,
            max(5, int(production_count * 0.05))
        )

        cursor.execute("""
        INSERT INTO production_logs(
            date,
            machine_id,
            planned_runtime_minutes,
            actual_runtime_minutes,
            downtime_minutes,
            production_count,
            rejection_count,
            target_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            current_date,
            machine_id,
            planned_runtime,
            actual_runtime,
            downtime,
            production_count,
            rejection_count,
            target_count
        ))

# ==================================================
# DOWNTIME LOGS
# ==================================================

reasons = [
    "Tool Change",
    "Maintenance",
    "Power Failure",
    "Operator Break",
    "Material Shortage",
    "Sensor Fault",
    "Machine Calibration",
    "Hydraulic Issue"
]

for _ in range(150):

    machine_id = random.choice(list(targets.keys()))

    date = (
        start_date +
        timedelta(days=random.randint(0, 59))
    ).strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO downtime_logs(
        date,
        machine_id,
        reason,
        downtime_minutes
    )
    VALUES (?, ?, ?, ?)
    """,
    (
        date,
        machine_id,
        random.choice(reasons),
        random.randint(15, 90)
    ))

# ==================================================
# MACHINE ALERTS
# ==================================================

alert_types = [
    "High Temperature",
    "Vibration Alert",
    "Power Fluctuation",
    "Pressure Drop",
    "Lubrication Warning",
    "Motor Overload",
    "Low Coolant Level"
]

severity_levels = [
    "Low",
    "Medium",
    "High"
]

for _ in range(100):

    machine_id = random.choice(list(targets.keys()))

    random_date = start_date + timedelta(
        days=random.randint(0, 59),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

    timestamp = random_date.strftime("%Y-%m-%d %H:%M")

    cursor.execute("""
    INSERT INTO machine_alerts(
        timestamp,
        machine_id,
        alert_type,
        severity
    )
    VALUES (?, ?, ?, ?)
    """,
    (
        timestamp,
        machine_id,
        random.choice(alert_types),
        random.choice(severity_levels)
    ))

# ==================================================
# SAVE
# ==================================================

conn.commit()
conn.close()

print("Sample manufacturing dataset created successfully!")