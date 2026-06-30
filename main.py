from datetime import date
from fastapi import FastAPI, HTTPException, Query

from analytics.analytics_engine import (
    calculate_oee,
    get_downtime_analytics,
    get_rejection_analytics,
    compare_machine_analytics,
    get_production_summary
)

from backend.database import get_connection
from backend.models import APIResponse, HealthResponse

from backend.validators import (
    validate_date_range,
    validate_machine_exists,
    validate_different_machines
)


app = FastAPI(
    title="AI Manufacturing Assistant",
    description="Manufacturing Analytics API built using FastAPI and SQLite",
    version="1.0.0"
)


def success_response(message: str, data):
    return {
        "status": "success",
        "message": message,
        "data": data
    }


def validate_result(result, error_message):
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=error_message
        )

    return result


@app.get(
    "/",
    response_model=HealthResponse,
    tags=["System"],
    summary="API Health Check"
)
def home():
    return {
        "message": "AI Manufacturing Assistant API is running successfully"
    }


@app.get(
    "/oee",
    response_model=APIResponse,
    tags=["Analytics"],
    summary="Calculate Overall Equipment Effectiveness"
)
def oee(
    machine_id: str = Query(..., min_length=1),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    try:

        validate_date_range(
            start_date,
            end_date
        )

        machine_id = machine_id.strip().upper()

        validate_machine_exists(
            machine_id
        )

        result = calculate_oee(
            machine_id,
            str(start_date),
            str(end_date)
        )

        validate_result(
            result,
            "No OEE data found"
        )

        return success_response(
            "OEE calculated successfully",
            result
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OEE calculation failed: {str(e)}"
        )


@app.get(
    "/downtime",
    response_model=APIResponse,
    tags=["Analytics"],
    summary="Get Machine Downtime Analytics"
)
def downtime(
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    try:

        validate_date_range(
            start_date,
            end_date
        )

        result = get_downtime_analytics(
            str(start_date),
            str(end_date)
        )

        validate_result(
            result,
            "No downtime data found"
        )

        return success_response(
            "Downtime analytics generated successfully",
            result
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Downtime analytics failed: {str(e)}"
        )


@app.get(
    "/rejection",
    response_model=APIResponse,
    tags=["Analytics"],
    summary="Get Rejection Analytics"
)
def rejection(
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    try:

        validate_date_range(
            start_date,
            end_date
        )

        result = get_rejection_analytics(
            str(start_date),
            str(end_date)
        )

        validate_result(
            result,
            "No rejection data found"
        )

        return success_response(
            "Rejection analytics generated successfully",
            result
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rejection analytics failed: {str(e)}"
        )


@app.get(
    "/compare",
    response_model=APIResponse,
    tags=["Analytics"],
    summary="Compare Machine Performance"
)
def compare(
    machine1: str = Query(
        ...,
        min_length=1,
        description="First Machine ID"
    ),
    machine2: str = Query(
        ...,
        min_length=1,
        description="Second Machine ID"
    ),
    start_date: date = Query(
        ...,
        description="Start Date (YYYY-MM-DD)"
    ),
    end_date: date = Query(
        ...,
        description="End Date (YYYY-MM-DD)"
    )
):
    try:

        # Validate date range
        validate_date_range(
            start_date,
            end_date
        )

        # Normalize machine IDs
        machine1 = machine1.strip().upper()
        machine2 = machine2.strip().upper()

        # Ensure different machines
        validate_different_machines(
            machine1,
            machine2
        )

        # Validate machine existence
        validate_machine_exists(
            machine1
        )

        validate_machine_exists(
            machine2
        )

        # Generate comparison
        result = compare_machine_analytics(
            machine1,
            machine2,
            str(start_date),
            str(end_date)
        )

        validate_result(
            result,
            "No comparison data found"
        )

        return success_response(
            "Machine comparison completed successfully",
            result
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Machine comparison failed: {str(e)}"
        )

@app.get(
    "/production-summary",
    response_model=APIResponse,
    tags=["Analytics"],
    summary="Generate Production Summary Report"
)
def production_summary():

    conn = None

    try:

        conn = get_connection()

        result = get_production_summary()

        validate_result(
            result,
            "No production data found"
        )

        return success_response(
            "Production summary generated successfully",
            result
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Production summary failed: {str(e)}"
        )

    finally:
        if conn:
            conn.close()