"""Parse OpenAPI specifications and extract endpoint shapes."""

from __future__ import annotations

from pathlib import Path

from prance import ResolvingParser

# Declarative list of endpoints the app will actually call; adjust as code evolves
NEEDED: dict[str, list[str]] = {
    "jira": ["GET /rest/api/2/myself", "GET /rest/api/2/project/{projectIdOrKey}"],
    "zephyr": ["GET /rest/atm/1.0/testcase/search", "GET /rest/atm/1.0/testrun/search"],
    "qtest": [
        "GET /api/v3/users/me",
        "GET /api/v3/projects",
        "GET /api/v3/projects/{projectId}/test-cases",
    ],
}


def _load(path) -> dict:
    """Load OpenAPI specification from file."""
    return ResolvingParser(str(path)).specification


def _find_operation_map(spec: dict) -> dict:
    """Find all operations in the OpenAPI spec."""
    ops = {}
    paths: dict = spec.get("paths", {})

    for path, methods in paths.items():
        for method, detail in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            ops[f"{method.upper()} {path}"] = detail

    return ops


def _fields_from_schema(schema: dict) -> list[dict]:
    """Extract field information from a JSON schema."""
    fields = []
    if not schema:
        return fields

    schema_type = schema.get("type")

    if schema_type == "object":
        props = schema.get("properties", {})
        for name, sub_schema in props.items():
            fields.append({"name": name, "type": sub_schema.get("type", "any")})
    elif schema_type == "array":
        fields.append({"name": "items", "type": "array"})
    else:
        fields.append({"name": "value", "type": schema_type or "any"})

    return fields


def extract_shapes(files: dict[str, Path]) -> dict[str, dict[str, dict]]:
    """
    Extract endpoint shapes from OpenAPI specification files.

    Args:
        files: Dictionary mapping API names to specification file paths

    Returns:
        Dictionary with API shapes for needed endpoints
    """
    out = {}

    for api, path in files.items():
        spec = _load(path)
        ops = _find_operation_map(spec)
        selected = {}
        needed = NEEDED.get(api, [])

        for op in needed:
            if op not in ops:
                continue

            operation_detail = ops[op]

            # Extract parameters
            params = []
            for param in operation_detail.get("parameters", []):
                params.append(
                    {
                        "name": param["name"],
                        "in": param.get("in", "query"),
                        "required": param.get("required", False),
                    }
                )

            # Extract response schema (try 200 first, then first available)
            responses = operation_detail.get("responses", {})
            response_200 = responses.get("200") or next(iter(responses.values()), {})
            content = (response_200.get("content") or {}).get("application/json") or {}
            schema = content.get("schema") or {}

            selected[op] = {"params": params, "response": {"fields": _fields_from_schema(schema)}}

        out[api] = selected

    return out
