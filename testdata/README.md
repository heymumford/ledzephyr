# Test Data Directory Structure

This directory contains all test data organized by purpose for the balanced testing architecture.

## Directory Structure

```
testdata/
├── cassettes/          # VCR cassettes for API replay
├── expected/           # Expected output files for validation
├── fixtures/           # Golden test data and input files
├── manifests/          # TDM manifest configuration files
└── masks/              # Data masking rules and examples
```

## Directory Purposes

### `cassettes/`
- **Purpose**: VCR-style HTTP interaction recordings
- **Usage**: E2E tests with replay mode
- **Format**: YAML files with request/response pairs
- **Security**: Scrubbed of sensitive data (tokens, emails)

### `expected/`
- **Purpose**: Expected output files for validation
- **Usage**: Quality gates and checksum validation
- **Format**: JSON, CSV, or other output formats
- **Maintenance**: Updated when calculations change

### `fixtures/`
- **Purpose**: Input data for golden file testing
- **Usage**: Unit and integration tests
- **Format**: JSON files with deterministic test data
- **Structure**: Separate input/output pairs for validation

### `manifests/`
- **Purpose**: TDM configuration files
- **Usage**: Define test scenarios and data sources
- **Format**: YAML files following manifest schema
- **Validation**: All manifests must pass schema validation

### `masks/`
- **Purpose**: Data masking rules and examples
- **Usage**: Demonstrate data anonymization
- **Format**: YAML rule definitions
- **Security**: Define field-level masking operations

## Naming Conventions

- Use descriptive names with underscores: `demo_project_2025q2.yaml`
- Include version/date information where relevant
- Keep filenames short but meaningful
- Use consistent extensions: `.yaml`, `.json`, `.csv`

## Data Quality Standards

- All files must be valid in their respective formats
- Manifests must pass JSON schema validation
- Cassettes must be scrubbed of sensitive information
- Golden files must be deterministic and reproducible