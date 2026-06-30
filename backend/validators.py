from datetime import date
from fastapi import HTTPException

from backend.database import get_connection


def validate_date_range(start_date: date, end_date: date):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be greater than end date"
        )


def validate_machine_exists(machine_id: str):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT machine_id
            FROM machines
            WHERE UPPER(machine_id) = UPPER(?)
            """,
            (machine_id,)
        )

        machine = cursor.fetchone()

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail=f"Machine '{machine_id}' not found"
            )

        return machine[0]

    finally:
        conn.close()


def validate_different_machines(machine1: str, machine2: str):
    if machine1.upper() == machine2.upper():
        raise HTTPException(
            status_code=400,
            detail="Please select two different machines"
        )