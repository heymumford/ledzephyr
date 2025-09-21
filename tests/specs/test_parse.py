"""Test OpenAPI specification parsing and endpoint extraction."""

import json

import pytest

from migrate_specs import parse

# Endpoints that our codebase actually uses
NEEDED = {
    "jira": ["GET /rest/api/2/myself", "GET /rest/api/2/project/{projectIdOrKey}"],
    "zephyr": ["GET /rest/atm/1.0/testcase/search", "GET /rest/atm/1.0/testrun/search"],
    "qtest": [
        "GET /api/v3/users/me",
        "GET /api/v3/projects",
        "GET /api/v3/projects/{projectId}/test-cases",
    ],
}


@pytest.mark.unit
def test_extract_needed_endpoints(tmp_path, monkeypatch):
    """Test extracting needed endpoints from OpenAPI specs."""
    # Arrange - patch the NEEDED constant
    monkeypatch.setattr(parse, "NEEDED", NEEDED)

    # Create mock OpenAPI specs with our needed endpoints
    jira_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Jira API", "version": "2.0"},
        "paths": {
            "/rest/api/2/myself": {
                "get": {
                    "parameters": [
                        {
                            "name": "expand",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "emailAddress": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/rest/api/2/project/{projectIdOrKey}": {
                "get": {
                    "parameters": [
                        {
                            "name": "projectIdOrKey",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    }

    zephyr_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Zephyr API", "version": "1.0"},
        "paths": {
            "/rest/atm/1.0/testcase/search": {
                "get": {
                    "parameters": [
                        {
                            "name": "projectKey",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "values": {"type": "array", "items": {"type": "object"}}
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/rest/atm/1.0/testrun/search": {
                "get": {
                    "parameters": [
                        {
                            "name": "testCaseKey",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"type": "object"}}
                                }
                            },
                        }
                    },
                }
            },
        },
    }

    qtest_spec = {
        "openapi": "3.0.0",
        "info": {"title": "qTest API", "version": "3.0"},
        "paths": {
            "/api/v3/users/me": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "username": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    }
                }
            },
            "/api/v3/projects": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    }
                }
            },
            "/api/v3/projects/{projectId}/test-cases": {
                "get": {
                    "parameters": [
                        {
                            "name": "projectId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "items": {"type": "array", "items": {"type": "object"}}
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    }

    # Create spec files
    jira_file = tmp_path / "jira.yaml"
    zephyr_file = tmp_path / "zephyr.yaml"
    qtest_file = tmp_path / "qtest.yaml"

    jira_file.write_text(json.dumps(jira_spec))
    zephyr_file.write_text(json.dumps(zephyr_spec))
    qtest_file.write_text(json.dumps(qtest_spec))

    files = {"jira": jira_file, "zephyr": zephyr_file, "qtest": qtest_file}

    # Act
    summary = parse.extract_shapes(files)

    # Assert - ensure we have minimal shapes for gold data
    for api, ops in NEEDED.items():
        assert api in summary
        for op in ops:
            assert op in summary[api], f"Missing operation {op} in {api}"
            shape = summary[api][op]
            assert "params" in shape
            assert "response" in shape
            assert len(shape["response"]["fields"]) > 0


@pytest.mark.unit
def test_fields_from_schema_object():
    """Test extracting fields from object schemas."""
    # Test object schema
    object_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "active": {"type": "boolean"},
        },
    }

    fields = parse._fields_from_schema(object_schema)

    assert len(fields) == 3
    assert {"name": "name", "type": "string"} in fields
    assert {"name": "age", "type": "integer"} in fields
    assert {"name": "active", "type": "boolean"} in fields


@pytest.mark.unit
def test_fields_from_schema_array():
    """Test extracting fields from array schemas."""
    array_schema = {"type": "array", "items": {"type": "object"}}

    fields = parse._fields_from_schema(array_schema)

    assert len(fields) == 1
    assert {"name": "items", "type": "array"} in fields


@pytest.mark.unit
def test_fields_from_schema_primitive():
    """Test extracting fields from primitive schemas."""
    string_schema = {"type": "string"}

    fields = parse._fields_from_schema(string_schema)

    assert len(fields) == 1
    assert {"name": "value", "type": "string"} in fields
