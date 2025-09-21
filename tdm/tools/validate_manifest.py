#!/usr/bin/env python3
"""Manifest validation tool for ledzephyr TDM."""

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
import yaml


def load_schema() -> dict[str, Any]:
    """Load the manifest JSON schema."""
    schema_path = Path(__file__).parent.parent / "schema" / "manifest.schema.json"
    with open(schema_path) as f:
        return json.load(f)


def load_manifest(manifest_path: str) -> dict[str, Any]:
    """Load and parse a YAML manifest file."""
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def validate_manifest(manifest_path: str) -> bool:
    """Validate a manifest against the schema.

    Returns:
        True if valid, False if invalid

    Raises:
        FileNotFoundError: If manifest or schema file not found
        yaml.YAMLError: If manifest is invalid YAML
        jsonschema.SchemaError: If schema itself is invalid
    """
    try:
        schema = load_schema()
        manifest = load_manifest(manifest_path)

        # Validate against schema
        jsonschema.validate(manifest, schema)

        # Additional business logic validation
        _validate_business_rules(manifest)

        print(f"✅ Manifest {manifest_path} is valid")
        return True

    except jsonschema.ValidationError as e:
        print(f"❌ Schema validation failed: {e.message}")
        if e.absolute_path:
            print(f"   Path: {'.'.join(str(p) for p in e.absolute_path)}")
        return False

    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


def _validate_business_rules(manifest: dict[str, Any]) -> None:
    """Validate business-specific rules beyond JSON schema."""

    # Check that cassette files exist for replay sources
    for source_name, source_config in manifest.get("sources", {}).items():
        if source_config.get("mode") == "replay":
            cassette_path = source_config.get("cassette")
            if cassette_path and not Path(cassette_path).exists():
                raise ValueError(f"Cassette file not found: {cassette_path}")

    # Check expected checksum file exists if specified
    quality_gates = manifest.get("quality_gates", {})
    if "expected_checksum" in quality_gates:
        # For now, just validate format - actual file checking happens during test run
        checksum = quality_gates["expected_checksum"]
        if len(checksum) != 64 or not all(c in "0123456789abcdef" for c in checksum):
            raise ValueError("Expected checksum must be a 64-character hex string")


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: validate_manifest.py <manifest.yaml>")
        sys.exit(1)

    manifest_path = sys.argv[1]

    if not Path(manifest_path).exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        sys.exit(1)

    is_valid = validate_manifest(manifest_path)
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
