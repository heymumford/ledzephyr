#!/usr/bin/env python3
"""
Download and process OpenAPI specs for vendor APIs.
"""

import json
from pathlib import Path

SPECS = {
    "jira": {
        "url": "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.json",
        "subset_paths": [
            "/rest/api/3/project/{projectIdOrKey}",
            "/rest/api/3/search",
            "/rest/api/3/issue/{issueIdOrKey}",
            "/rest/api/3/myself",
        ],
    },
    "zephyr": {
        # Zephyr Scale doesn't provide public OpenAPI, we'll create a minimal one
        "manual": True,
        "paths": {
            "/testcases": ["GET", "POST"],
            "/testcases/{id}": ["GET", "PUT", "DELETE"],
            "/testcycles": ["GET", "POST"],
            "/testexecutions": ["GET", "POST"],
        },
    },
    "qtest": {
        # qTest API spec - we'll create a minimal subset
        "manual": True,
        "paths": {
            "/api/v3/projects": ["GET"],
            "/api/v3/projects/{projectId}/test-cases": ["GET", "POST"],
            "/api/v3/projects/{projectId}/test-runs": ["GET", "POST"],
            "/api/v3/projects/{projectId}/test-cycles": ["GET"],
        },
    },
}


def create_minimal_spec(name, config):
    """Create minimal OpenAPI spec for APIs without public specs."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": f"{name.title()} API", "version": "1.0.0"},
        "servers": [{"url": f"https://api.{name}.example.com"}],
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        },
    }

    # Add paths
    for path, methods in config.get("paths", {}).items():
        spec["paths"][path] = {}
        for method in methods:
            spec["paths"][path][method.lower()] = {
                "summary": f"{method} {path}",
                "operationId": f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }

            # Add path parameters
            if "{" in path:
                params = []
                for part in path.split("/"):
                    if part.startswith("{") and part.endswith("}"):
                        param_name = part[1:-1]
                        params.append(
                            {
                                "name": param_name,
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        )
                spec["paths"][path][method.lower()]["parameters"] = params

    return spec


def download_jira_spec_subset():
    """Download and extract subset of Jira API spec."""
    # For now, create a minimal spec
    spec = create_minimal_spec(
        "jira",
        {
            "paths": {
                "/rest/api/3/project/{projectIdOrKey}": ["GET"],
                "/rest/api/3/search": ["GET", "POST"],
                "/rest/api/3/issue/{issueIdOrKey}": ["GET"],
                "/rest/api/3/myself": ["GET"],
            }
        },
    )

    # Add Jira-specific schemas
    spec["components"]["schemas"]["Project"] = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "key": {"type": "string"},
            "name": {"type": "string"},
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                },
            },
        },
    }

    spec["components"]["schemas"]["Issue"] = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "key": {"type": "string"},
            "fields": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "status": {"type": "object", "properties": {"name": {"type": "string"}}},
                    "assignee": {
                        "type": "object",
                        "properties": {"emailAddress": {"type": "string"}},
                    },
                },
            },
        },
    }

    return spec


def main():
    """Download and process all specs."""
    specs_dir = Path(__file__).parent

    # Process Jira
    print("Creating Jira API spec subset...")
    jira_spec = download_jira_spec_subset()
    with open(specs_dir / "jira-api.json", "w") as f:
        json.dump(jira_spec, f, indent=2)

    # Process Zephyr
    print("Creating Zephyr Scale API spec...")
    zephyr_spec = create_minimal_spec("zephyr", SPECS["zephyr"])

    # Add Zephyr-specific schemas
    zephyr_spec["components"]["schemas"]["TestCase"] = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "key": {"type": "string"},
            "name": {"type": "string"},
            "projectId": {"type": "integer"},
            "status": {"type": "string"},
            "labels": {"type": "array", "items": {"type": "string"}},
        },
    }

    with open(specs_dir / "zephyr-api.json", "w") as f:
        json.dump(zephyr_spec, f, indent=2)

    # Process qTest
    print("Creating qTest API spec...")
    qtest_spec = create_minimal_spec("qtest", SPECS["qtest"])

    # Add qTest-specific schemas
    qtest_spec["components"]["schemas"]["TestCase"] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "test_case_version_id": {"type": "integer"},
            "project_id": {"type": "integer"},
        },
    }

    with open(specs_dir / "qtest-api.json", "w") as f:
        json.dump(qtest_spec, f, indent=2)

    print("✅ All API specs created successfully!")
    print(f"  - {specs_dir}/jira-api.json")
    print(f"  - {specs_dir}/zephyr-api.json")
    print(f"  - {specs_dir}/qtest-api.json")


if __name__ == "__main__":
    main()
