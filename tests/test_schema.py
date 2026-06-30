import pytest
from llm.function_schemas import FUNCTION_SCHEMAS


def test_schema_exists():
    assert isinstance(FUNCTION_SCHEMAS, list)
    assert len(FUNCTION_SCHEMAS) > 0


def test_schema_names_unique():
    names = [schema["name"] for schema in FUNCTION_SCHEMAS]
    assert len(names) == len(set(names))


def test_schema_required_fields():
    for schema in FUNCTION_SCHEMAS:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema


def test_parameters_type():
    for schema in FUNCTION_SCHEMAS:
        assert isinstance(schema["parameters"], dict)