import pytest

from backend.function_registry import (
    get_plant_production_summary,
    get_machine_maintenance_recommendation,
)


def test_production_function_exists():
    assert callable(get_plant_production_summary)


def test_maintenance_function_exists():
    assert callable(get_machine_maintenance_recommendation)


def test_registry_functions_callable():
    functions = [
        get_plant_production_summary,
        get_machine_maintenance_recommendation,
    ]

    for fn in functions:
        assert callable(fn)