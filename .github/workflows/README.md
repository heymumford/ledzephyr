# GitHub Actions Workflows

This directory contains standardized GitHub Actions workflows following industry best practices.

## Workflow Overview

### Core Workflows

| Workflow | Purpose | Triggers | Duration |
|----------|---------|----------|----------|
| [`ci.yml`](./ci.yml) | Continuous Integration | Push, PR | ~5 min |
| [`cd.yml`](./cd.yml) | Continuous Deployment | Release, Manual | ~15 min |

### Test Workflows

| Workflow | Purpose | Test Type | Triggers |
|----------|---------|-----------|----------|
| [`test-unit.yml`](./test-unit.yml) | Unit Tests | Fast, isolated | Push, PR |
| [`test-integration.yml`](./test-integration.yml) | Integration Tests | Service integration | Push, PR |
| [`test-e2e.yml`](./test-e2e.yml) | End-to-End Tests | Full workflows | Push, PR |
| [`test-matrix.yml`](./test-matrix.yml) | Matrix Testing | Multi-dimensional | Push, PR |
| [`test-performance.yml`](./test-performance.yml) | Performance Tests | Benchmarks | Weekly, Manual |

### Orchestration Workflows

| Workflow | Purpose | Triggers | Frequency |
|----------|---------|----------|-----------|
| [`orchestrator.yml`](./orchestrator.yml) | Test Coordination | Push, PR | On demand |
| [`coordinator.yml`](./coordinator.yml) | Work Prioritization | Schedule | Every 4 min |
| [`ai-assessment.yml`](./github-ai-assessment.yml) | AI Analysis | Schedule | Hourly |

### Utility Workflows

| Workflow | Purpose | Triggers |
|----------|---------|----------|
| [`debug-logs.yml`](./debug-logs.yml) | Debug & Logging | Manual |

## Naming Conventions

### Workflow Files
- Use kebab-case: `test-unit.yml`
- Prefix by category: `test-`, `deploy-`, `debug-`
- Keep names concise and descriptive

### Job Names
- Use Title Case: `Unit Tests`
- Be descriptive: `Integration - Observability`
- Group related jobs: `Build & Package`

### Step Names
- Use action-oriented names: `Run tests`, `Deploy to staging`
- Be specific: `Upload test results`
- Use consistent formatting

## Standards Applied

### Concurrency Controls
All workflows include proper concurrency management:
```yaml
concurrency:
  group: workflow-name-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Permissions
Minimal required permissions following principle of least privilege:
```yaml
permissions:
  contents: read
  checks: write
```

### Timeouts
All jobs have appropriate timeout limits:
```yaml
timeout-minutes: 15
```

### Caching
Consistent dependency caching:
```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pypoetry
    key: poetry-${{ env.CACHE_VERSION }}-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
```

### Artifact Management
Standardized artifact upload/download:
```yaml
- name: Upload test results
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results.xml
    retention-days: 7
```

### Error Handling
Proper error handling and status reporting:
```yaml
- name: Check results
  if: always()
  run: |
    if [[ "${{ needs.job.result }}" == "failure" ]]; then
      echo "❌ Job failed"
      exit 1
    fi
```

## Environment Variables

Global environment variables used across workflows:

```yaml
env:
  PYTHON_VERSION: '3.11'
  POETRY_VERSION: '1.7.0'
  CACHE_VERSION: '1'
```

## Branch Protection

Recommended branch protection rules for `main`:
- Require status checks: `CI`, `Unit Tests`
- Require up-to-date branches
- Require conversation resolution
- Restrict pushes to admins only

## Security

### Secrets Management
- Use GitHub Secrets for sensitive data
- Rotate secrets regularly
- Use environment-specific secrets

### OIDC Configuration
Workflows support OpenID Connect for secure cloud deployments:
```yaml
permissions:
  id-token: write
```

## Monitoring

### Workflow Metrics
- Success/failure rates tracked
- Execution time monitoring
- Resource usage analysis

### Notifications
- Failed workflow notifications
- Deployment status updates
- Performance degradation alerts

## Best Practices

1. **Keep workflows focused** - Single responsibility principle
2. **Use caching** - Speed up builds with proper caching
3. **Fail fast** - Use `--maxfail` and early validation
4. **Matrix testing** - Test across multiple dimensions
5. **Conditional execution** - Use `if` conditions to skip unnecessary steps
6. **Artifact retention** - Set appropriate retention periods
7. **Resource limits** - Use timeouts to prevent runaway processes

## Troubleshooting

### Common Issues
- **Permission errors**: Check workflow permissions and secrets
- **Cache misses**: Verify cache keys and paths
- **Timeout failures**: Increase timeout or optimize performance
- **Artifact errors**: Check retention policies and storage limits

### Debug Mode
Enable debug logging by setting:
```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

## Contributing

When adding new workflows:
1. Follow naming conventions
2. Include proper permissions and concurrency controls
3. Add appropriate timeouts and error handling
4. Update this documentation
5. Test in a feature branch first