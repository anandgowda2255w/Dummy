from backend.database import get_connection


# ==================================================
# HELPER: GET DATE RANGE FROM DB
# ==================================================

def get_db_date_range():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(date), MAX(date) FROM production_logs")
    row = cursor.fetchone()
    conn.close()
    return {"min_date": row[0], "max_date": row[1]}


# ==================================================
# HELPER: GET ALL MACHINES
# ==================================================

def get_all_machines():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT machine_id, machine_name FROM machines ORDER BY machine_id")
    rows = cursor.fetchall()
    conn.close()
    return [{"machine_id": r[0], "machine_name": r[1]} for r in rows]


# ==================================================
# 1. CALCULATE OEE
# ==================================================

def calculate_oee(machine_id, start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            SUM(planned_runtime_minutes),
            SUM(actual_runtime_minutes),
            SUM(production_count),
            SUM(rejection_count),
            SUM(target_count)
        FROM production_logs
        WHERE machine_id = ?
        AND date BETWEEN ? AND ?
    """, (machine_id, start_date, end_date))
    result = cursor.fetchone()
    conn.close()

    if not result or result[0] is None:
        return {"status": "error", "message": f"No data found for machine {machine_id}"}

    planned_runtime, actual_runtime, production_count, rejection_count, target_count = result

    availability = actual_runtime / planned_runtime if planned_runtime and planned_runtime > 0 else 0
    performance = production_count / target_count if target_count and target_count > 0 else 0
    good_count = production_count - rejection_count
    quality = good_count / production_count if production_count and production_count > 0 else 0
    oee = availability * performance * quality

    return {
        "status": "success",
        "data": {
            "machine_id": machine_id,
            "start_date": start_date,
            "end_date": end_date,
            "availability": round(availability * 100, 2),
            "performance": round(performance * 100, 2),
            "quality": round(quality * 100, 2),
            "oee": round(oee * 100, 2),
            "planned_runtime": planned_runtime,
            "actual_runtime": actual_runtime,
            "production_count": production_count,
            "rejection_count": rejection_count,
            "good_count": good_count,
            "target_count": target_count
        },
        "message": ""
    }


# ==================================================
# 2. PLANT DOWNTIME ANALYTICS (all machines)
# ==================================================

def get_downtime_analytics(start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.machine_id,
            m.machine_name,
            SUM(p.downtime_minutes) as prod_downtime,
            COALESCE((
                SELECT SUM(d.downtime_minutes)
                FROM downtime_logs d
                WHERE d.machine_id = p.machine_id
                AND d.date BETWEEN ? AND ?
            ), 0) as log_downtime,
            GROUP_CONCAT(DISTINCT dl.reason) as reasons
        FROM production_logs p
        LEFT JOIN machines m ON p.machine_id = m.machine_id
        LEFT JOIN downtime_logs dl ON dl.machine_id = p.machine_id
            AND dl.date BETWEEN ? AND ?
        WHERE p.date BETWEEN ? AND ?
        GROUP BY p.machine_id, m.machine_name
        ORDER BY prod_downtime DESC
    """, (start_date, end_date, start_date, end_date, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        reasons = row[4].split(",") if row[4] else []
        unique_reasons = list(set(r.strip() for r in reasons))[:3]
        data.append({
            "machine_id": row[0],
            "machine_name": row[1] or row[0],
            "downtime_minutes": row[2] or 0,
            "reasons": unique_reasons
        })

    return {"status": "success", "data": data, "message": ""}


# ==================================================
# 3. MACHINE-SPECIFIC DOWNTIME
# ==================================================

def get_machine_downtime(machine_id, start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(downtime_minutes)
        FROM production_logs
        WHERE machine_id = ? AND date BETWEEN ? AND ?
    """, (machine_id, start_date, end_date))
    prod_row = cursor.fetchone()

    cursor.execute("""
        SELECT reason, SUM(downtime_minutes)
        FROM downtime_logs
        WHERE machine_id = ? AND date BETWEEN ? AND ?
        GROUP BY reason
        ORDER BY SUM(downtime_minutes) DESC
    """, (machine_id, start_date, end_date))
    reason_rows = cursor.fetchall()

    cursor.execute("""
        SELECT alert_type, COUNT(*), severity
        FROM machine_alerts
        WHERE machine_id = ? AND DATE(timestamp) BETWEEN ? AND ?
        GROUP BY alert_type, severity
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """, (machine_id, start_date, end_date))
    alert_rows = cursor.fetchall()

    conn.close()

    total_downtime = prod_row[0] or 0
    reasons = [{"reason": r[0], "minutes": r[1]} for r in reason_rows]
    alerts = [{"alert_type": r[0], "count": r[1], "severity": r[2]} for r in alert_rows]

    return {
        "status": "success",
        "data": {
            "machine_id": machine_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_downtime_minutes": total_downtime,
            "downtime_by_reason": reasons,
            "alerts": alerts
        },
        "message": ""
    }


# ==================================================
# 4. PLANT REJECTION ANALYTICS (all machines)
# ==================================================

def get_rejection_analytics(start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.machine_id,
            m.machine_name,
            SUM(p.rejection_count),
            SUM(p.production_count)
        FROM production_logs p
        LEFT JOIN machines m ON p.machine_id = m.machine_id
        WHERE p.date BETWEEN ? AND ?
        GROUP BY p.machine_id, m.machine_name
        ORDER BY SUM(p.rejection_count) DESC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        rejection_rate = round((row[2] / row[3]) * 100, 2) if row[3] and row[3] > 0 else 0
        data.append({
            "machine_id": row[0],
            "machine_name": row[1] or row[0],
            "rejection_count": row[2] or 0,
            "production_count": row[3] or 0,
            "rejection_rate": rejection_rate
        })

    return {"status": "success", "data": data, "message": ""}


# ==================================================
# 5. MACHINE-SPECIFIC REJECTION
# ==================================================

def get_machine_rejection(machine_id, start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            date,
            production_count,
            rejection_count,
            (production_count - rejection_count) as good_count
        FROM production_logs
        WHERE machine_id = ? AND date BETWEEN ? AND ?
        ORDER BY date
    """, (machine_id, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    total_prod = sum(r[1] for r in rows)
    total_rej = sum(r[2] for r in rows)
    daily_data = [{"date": r[0], "production": r[1], "rejection": r[2], "good": r[3]} for r in rows]

    return {
        "status": "success",
        "data": {
            "machine_id": machine_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_production": total_prod,
            "total_rejection": total_rej,
            "total_good": total_prod - total_rej,
            "rejection_rate": round((total_rej / total_prod) * 100, 2) if total_prod > 0 else 0,
            "daily_data": daily_data
        },
        "message": ""
    }


# ==================================================
# 6. COMPARE TWO MACHINES
# ==================================================

def compare_machine_analytics(machine1, machine2, start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    data = []
    for machine in [machine1, machine2]:
        cursor.execute("""
            SELECT
                SUM(production_count),
                SUM(downtime_minutes),
                SUM(rejection_count),
                SUM(planned_runtime_minutes),
                SUM(actual_runtime_minutes),
                SUM(target_count)
            FROM production_logs
            WHERE machine_id = ? AND date BETWEEN ? AND ?
        """, (machine, start_date, end_date))
        result = cursor.fetchone()
        if result and result[0] is not None:
            prod = result[0] or 0
            downtime = result[1] or 0
            rejection = result[2] or 0
            planned = result[3] or 1
            actual = result[4] or 0
            target = result[5] or 1
            good = prod - rejection
            availability = round((actual / planned) * 100, 2) if planned > 0 else 0
            performance = round((prod / target) * 100, 2) if target > 0 else 0
            quality = round((good / prod) * 100, 2) if prod > 0 else 0
            oee = round((availability / 100) * (performance / 100) * (quality / 100) * 100, 2)
            data.append({
                "machine_id": machine,
                "production": prod,
                "downtime": downtime,
                "rejection": rejection,
                "availability": availability,
                "performance": performance,
                "quality": quality,
                "oee": oee
            })
    conn.close()
    return {"status": "success", "data": data, "message": ""}


# ==================================================
# 7. PLANT PRODUCTION SUMMARY (all machines)
# ==================================================

def get_production_summary(start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute("""
            SELECT
                p.machine_id,
                m.machine_name,
                SUM(p.production_count),
                SUM(p.rejection_count),
                SUM(p.downtime_minutes),
                SUM(p.actual_runtime_minutes),
                SUM(p.planned_runtime_minutes)
            FROM production_logs p
            LEFT JOIN machines m ON p.machine_id = m.machine_id
            WHERE p.date BETWEEN ? AND ?
            GROUP BY p.machine_id, m.machine_name
            ORDER BY SUM(p.production_count) DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT
                p.machine_id,
                m.machine_name,
                SUM(p.production_count),
                SUM(p.rejection_count),
                SUM(p.downtime_minutes),
                SUM(p.actual_runtime_minutes),
                SUM(p.planned_runtime_minutes)
            FROM production_logs p
            LEFT JOIN machines m ON p.machine_id = m.machine_id
            GROUP BY p.machine_id, m.machine_name
            ORDER BY SUM(p.production_count) DESC
        """)
    rows = cursor.fetchall()
    conn.close()

    machine_data = []
    total_prod = total_rej = total_down = 0
    for row in rows:
        prod = row[2] or 0
        rej = row[3] or 0
        down = row[4] or 0
        actual = row[5] or 0
        planned = row[6] or 1
        good = prod - rej
        rej_rate = round((rej / prod) * 100, 2) if prod > 0 else 0
        util = round((actual / planned) * 100, 2) if planned > 0 else 0
        machine_data.append({
            "machine_id": row[0],
            "machine_name": row[1] or row[0],
            "production": prod,
            "rejection": rej,
            "good_units": good,
            "downtime_minutes": down,
            "rejection_rate": rej_rate,
            "utilization": util
        })
        total_prod += prod
        total_rej += rej
        total_down += down

    return {
        "status": "success",
        "data": {
            "start_date": start_date,
            "end_date": end_date,
            "total_production": total_prod,
            "total_rejection": total_rej,
            "total_good": total_prod - total_rej,
            "total_downtime": total_down,
            "overall_rejection_rate": round((total_rej / total_prod) * 100, 2) if total_prod > 0 else 0,
            "machines": machine_data
        },
        "message": ""
    }


# ==================================================
# 8. MACHINE-SPECIFIC PRODUCTION SUMMARY
# ==================================================

def get_machine_production_summary(machine_id, start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            date,
            production_count,
            rejection_count,
            downtime_minutes,
            actual_runtime_minutes,
            planned_runtime_minutes,
            target_count
        FROM production_logs
        WHERE machine_id = ? AND date BETWEEN ? AND ?
        ORDER BY date
    """, (machine_id, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    daily = []
    total_prod = total_rej = total_down = 0
    for row in rows:
        daily.append({
            "date": row[0],
            "production": row[1],
            "rejection": row[2],
            "downtime": row[3],
            "actual_runtime": row[4],
            "planned_runtime": row[5],
            "target": row[6]
        })
        total_prod += row[1] or 0
        total_rej += row[2] or 0
        total_down += row[3] or 0

    return {
        "status": "success",
        "data": {
            "machine_id": machine_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_production": total_prod,
            "total_rejection": total_rej,
            "total_good": total_prod - total_rej,
            "total_downtime": total_down,
            "rejection_rate": round((total_rej / total_prod) * 100, 2) if total_prod > 0 else 0,
            "daily_data": daily
        },
        "message": ""
    }


# ==================================================
# 9. MAINTENANCE RECOMMENDATIONS
# ==================================================

def get_maintenance_recommendation(start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT machine_id, SUM(downtime_minutes)
        FROM production_logs
        WHERE date BETWEEN ? AND ?
        GROUP BY machine_id
        ORDER BY SUM(downtime_minutes) DESC
        LIMIT 5
    """, (start_date, end_date))
    downtime_rows = cursor.fetchall()

    cursor.execute("""
        SELECT machine_id, alert_type, COUNT(*) as cnt, severity
        FROM machine_alerts
        WHERE DATE(timestamp) BETWEEN ? AND ?
        GROUP BY machine_id, alert_type, severity
        ORDER BY cnt DESC
    """, (start_date, end_date))
    alert_rows = cursor.fetchall()

    cursor.execute("""
        SELECT machine_id, SUM(rejection_count), SUM(production_count)
        FROM production_logs
        WHERE date BETWEEN ? AND ?
        GROUP BY machine_id
        ORDER BY SUM(rejection_count) DESC
        LIMIT 5
    """, (start_date, end_date))
    rejection_rows = cursor.fetchall()

    conn.close()

    recs = []
    for row in downtime_rows:
        mid, down = row[0], row[1]
        if down and down > 200:
            recs.append({
                "machine_id": mid,
                "issue": f"High downtime: {down} minutes",
                "recommendation": "Schedule preventive maintenance and review operating procedures"
            })

    alert_map = {}
    for row in alert_rows:
        mid, atype, cnt, sev = row
        if mid not in alert_map:
            alert_map[mid] = []
        alert_map[mid].append({"type": atype, "count": cnt, "severity": sev})

    for mid, alerts in alert_map.items():
        for a in alerts:
            if a["severity"] in ("High", "Critical") or a["count"] >= 3:
                recs.append({
                    "machine_id": mid,
                    "issue": f"{a['type']} alert ({a['count']} times, {a['severity']} severity)",
                    "recommendation": f"Immediate inspection required for {a['type'].lower()}"
                })

    for row in rejection_rows:
        mid, rej, prod = row[0], row[1], row[2]
        if prod and prod > 0:
            rate = (rej / prod) * 100
            if rate > 5:
                recs.append({
                    "machine_id": mid,
                    "issue": f"High rejection rate: {round(rate, 1)}%",
                    "recommendation": "Review quality control processes and tooling condition"
                })

    return {"status": "success", "data": recs, "message": ""}
