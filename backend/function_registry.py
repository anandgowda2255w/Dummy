from analytics.analytics_engine import (
    calculate_oee,
    get_downtime_analytics,
    get_machine_downtime,
    get_rejection_analytics,
    get_machine_rejection,
    compare_machine_analytics,
    get_production_summary,
    get_machine_production_summary,
    get_maintenance_recommendation,
    get_db_date_range,
    get_all_machines
)


def get_plant_production_summary(start_date, end_date):
    """Alias: plant-wide production summary (same as get_production_summary)."""
    return get_production_summary(start_date=start_date, end_date=end_date)


def get_machine_maintenance_recommendation(machine_id, start_date, end_date):
    """
    Machine-specific maintenance recommendation.

    Calls the existing plant-wide analytics function and filters its results
    to the requested machine_id.  The analytics engine is never modified.
    """
    result = get_maintenance_recommendation(start_date=start_date, end_date=end_date)

    if result.get("status") != "success":
        return result

    all_recs = result.get("data", [])
    machine_recs = [r for r in all_recs if r.get("machine_id", "").upper() == machine_id.upper()]

    return {
        "status": "success",
        "data": machine_recs,
        "message": "",
        # Carry machine_id so the frontend knows this is machine-specific
        "machine_id": machine_id.upper(),
    }


FUNCTION_REGISTRY = {
    "calculate_oee":                          calculate_oee,
    "get_downtime_analytics":                 get_downtime_analytics,
    "get_machine_downtime":                   get_machine_downtime,
    "get_rejection_analytics":                get_rejection_analytics,
    "get_machine_rejection":                  get_machine_rejection,
    "compare_machine_analytics":              compare_machine_analytics,
    "get_production_summary":                 get_production_summary,
    "get_plant_production_summary":           get_plant_production_summary,
    "get_machine_production_summary":         get_machine_production_summary,
    "get_maintenance_recommendation":         get_maintenance_recommendation,
    "get_machine_maintenance_recommendation": get_machine_maintenance_recommendation,
}
