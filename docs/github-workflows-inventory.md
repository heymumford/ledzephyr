# GitHub Workflows Inventory & Standardization

## 📋 Current Workflow Files

### Core Architecture Files
| File | Purpose | Status | Recommended Action |
|------|---------|--------|-------------------|
| `.github/actions/setup-python-poetry/action.yml` | Shared Python/Poetry setup | ✅ Good | Keep as-is |
| `.github/workflows/orchestrator.yml` | Main workflow orchestration | ⚠️ Needs standardization | Rename to `orchestrator-master.yml` |
| `.github/workflows/coordinator.yml` | Work coordination every 4 minutes | ⚠️ Needs standardization | Rename to `coordinator-agent.yml` |
| `.github/workflows/github-ai-assessment.yml` | AI-driven repository assessment | ✅ Good | Keep as-is |

### Testing Workflows
| File | Purpose | Status | Recommended Action |
|------|---------|--------|-------------------|
| `.github/workflows/ci.yml` | Continuous integration | ⚠️ Review needed | Standardize and possibly merge |
| `.github/workflows/cd.yml` | Continuous deployment | ⚠️ Review needed | Standardize format |
| `.github/workflows/test-unit.yml` | Unit testing | ⚠️ Consolidate | Merge into rail-based testing |
| `.github/workflows/test-integration.yml` | Integration testing | ⚠️ Consolidate | Merge into rail-based testing |
| `.github/workflows/test-e2e.yml` | End-to-end testing | ⚠️ Consolidate | Merge into rail-based testing |
| `.github/workflows/test-matrix.yml` | Matrix testing | ⚠️ Consolidate | Merge into rail-based testing |
| `.github/workflows/test-performance.yml` | Performance testing | ⚠️ Consolidate | Merge into rail-based testing |

### Utility Workflows
| File | Purpose | Status | Recommended Action |
|------|---------|--------|-------------------|
| `.github/workflows/debug-logs.yml` | Debug logging | ⚠️ Review needed | Standardize or remove |

## 🎯 Industry Standard Naming Convention

### Recommended Naming Structure
```
.github/
├── actions/
│   └── setup-python-poetry/
│       └── action.yml                    # ✅ Good
├── workflows/
│   ├── orchestrator-master.yml          # Main orchestration
│   ├── coordinator-agent.yml            # Work coordination
│   ├── github-ai-assessment.yml         # ✅ Already good
│   ├── rail-1-core-business-logic.yml   # Pure business logic
│   ├── rail-2-infrastructure-services.yml # Infrastructure services
│   ├── rail-3-external-integrations.yml # External APIs
│   ├── parallel-testing-matrix.yml      # Cross-platform matrix
│   ├── parallel-performance-testing.yml # Performance benchmarks
│   ├── ci-pull-request.yml             # PR validation
│   ├── cd-release.yml                  # Release deployment
│   └── maintenance-cleanup.yml         # Periodic maintenance
```

## 📏 Standard YAML Structure Template

### Workflow File Structure
```yaml
name: Descriptive Workflow Name

on:
  push:
    branches: [ main, develop, 'feat/*' ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      parameter_name:
        description: 'Clear description'
        required: false
        default: 'default_value'
        type: choice
        options:
          - option1
          - option2

# Global environment variables
env:
  PYTHON_VERSION: '3.11'
  POETRY_VERSION: '1.7.0'

# Workflow-level permissions
permissions:
  contents: read
  actions: read

jobs:
  job-name:
    name: Human Readable Job Name
    runs-on: ubuntu-latest

    # Job-level permissions (if different from workflow)
    permissions:
      contents: read

    # Conditional execution
    if: github.event_name != 'pull_request' || github.event.pull_request.draft == false

    # Job timeout
    timeout-minutes: 30

    # Strategy for matrix builds
    strategy:
      fail-fast: false
      matrix:
        parameter: [value1, value2, value3]
        include:
          - parameter: value1
            additional: extra1
        exclude:
          - parameter: value2

    # Environment variables for this job
    env:
      JOB_SPECIFIC_VAR: value

    # Job outputs
    outputs:
      output_name: ${{ steps.step-id.outputs.output_name }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python & Poetry
        uses: ./.github/actions/setup-python-poetry
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          poetry-version: ${{ env.POETRY_VERSION }}

      - name: Action step with clear description
        id: step-id
        run: |
          echo "Multi-line script"
          echo "with proper formatting"
        env:
          STEP_SPECIFIC_VAR: ${{ secrets.SECRET_NAME }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: descriptive-artifact-name
          path: path/to/artifacts
          retention-days: 7
```

## 🔄 Standardization Actions Required

### 1. Rename Core Files
```bash
# Rename core orchestration files for consistency
mv .github/workflows/orchestrator.yml .github/workflows/orchestrator-master.yml
mv .github/workflows/coordinator.yml .github/workflows/coordinator-agent.yml
```

### 2. Consolidate Testing Workflows
Create three main rail-based testing workflows:
- `rail-1-core-business-logic.yml` - Pure computational logic
- `rail-2-infrastructure-services.yml` - Infrastructure with controlled dependencies
- `rail-3-external-integrations.yml` - External APIs with heavy mocking

### 3. Standardize Existing Workflows

#### Required Updates for All Workflows:
1. **Consistent naming**: Use kebab-case for all file names
2. **Standard permissions**: Explicit permissions declarations
3. **Timeout settings**: All jobs should have timeout-minutes
4. **Error handling**: Proper continue-on-error and if conditions
5. **Artifact naming**: Consistent naming scheme with retention policies
6. **Environment variables**: Centralized in env section
7. **Action versions**: Pin to specific versions (e.g., @v4, not @latest)

#### Metadata Standards:
```yaml
name: Clear Descriptive Name
# Description comment explaining purpose
# Rail assignment if applicable
# Dependencies and relationships

on:
  # Always include workflow_dispatch for manual testing
  workflow_dispatch:
  # Standard trigger patterns
  push:
    branches: [ main, develop, 'feat/*' ]
  pull_request:
    branches: [ main ]
```

### 4. Documentation Standards

Each workflow should have:
- Clear name and description
- Purpose and scope comment at top
- Rail assignment (if applicable)
- Dependencies clearly documented
- Input/output specifications
- Artifact specifications

## 🎯 Migration Plan

### Phase 1: Core Infrastructure (Week 1)
1. Rename orchestrator.yml → orchestrator-master.yml
2. Rename coordinator.yml → coordinator-agent.yml
3. Standardize github-ai-assessment.yml format
4. Update setup-python-poetry action

### Phase 2: Rail-Based Testing (Week 2)
1. Create rail-1-core-business-logic.yml
2. Create rail-2-infrastructure-services.yml
3. Create rail-3-external-integrations.yml
4. Migrate test-* workflows into rails

### Phase 3: CI/CD Standardization (Week 3)
1. Rename ci.yml → ci-pull-request.yml
2. Rename cd.yml → cd-release.yml
3. Create parallel-testing-matrix.yml
4. Create parallel-performance-testing.yml

### Phase 4: Cleanup (Week 4)
1. Remove redundant workflows
2. Update all documentation
3. Validate with workflow validator
4. Test complete parallel architecture

## 📊 Quality Metrics

### Standards Compliance Checklist
- [ ] All workflows use consistent naming convention
- [ ] All workflows have explicit permissions
- [ ] All workflows have timeout settings
- [ ] All workflows use pinned action versions
- [ ] All workflows have proper error handling
- [ ] All artifacts use consistent naming
- [ ] All secrets follow naming convention
- [ ] All workflows have documentation headers

### Performance Targets
- Maximum workflow duration: 15 minutes
- Maximum parallel jobs per workflow: 20
- Artifact retention: 7 days (configurable)
- Cache hit rate: >80% for dependencies

## 🔗 Related Documentation
- [GitHub Actions Secrets Setup](./github-actions-secrets-setup.md)
- [Parallel Testing Architecture](./parallel-github-actions-architecture.md)
- [Workflow Validation Scripts](../scripts/validate-workflows.py)