# GitHub Actions Workflows Documentation

## Overview

LedZephyr uses a comprehensive GitHub Actions architecture following industry standards for CI/CD automation, testing, and deployment workflows.

## Workflow Categories

### 🔄 Core CI/CD Workflows

#### CI Workflow (`ci.yml`)
- **Purpose**: Continuous Integration with lint, security, and basic tests
- **Triggers**: Push to main/develop, Pull Requests
- **Duration**: ~5 minutes
- **Jobs**:
  - `lint` - Code formatting and style checks (black, ruff, mypy)
  - `security` - Security scanning (bandit)
  - `test-basic` - Essential test suite with coverage
  - `ci-status` - Aggregated status reporting

#### CD Workflow (`cd.yml`)
- **Purpose**: Continuous Deployment with build, test, and release
- **Triggers**: Release events, Manual deployment
- **Duration**: ~15 minutes
- **Jobs**:
  - `build` - Package building and Docker image creation
  - `test-deployment` - Deployment smoke tests
  - `deploy-staging` - Staging environment deployment
  - `deploy-production` - Production deployment
  - `notify` - Deployment notifications

### 🧪 Test Workflows

#### Unit Tests (`test-unit.yml`)
- **Purpose**: Fast, isolated unit tests for core business logic
- **Triggers**: Push, PR, Manual
- **Jobs**:
  - `unit-calculations` - Mathematical and calculation logic
  - `data-validation` - Validators, models, configuration
  - `algorithm-properties` - Property-based testing
  - `business-logic-integration` - Cross-module workflows

#### Integration Tests (`test-integration.yml`)
- **Purpose**: Service integration with controlled dependencies
- **Triggers**: Push, PR, Manual
- **Jobs**:
  - `integration-observability` - Monitoring and metrics
  - `caching-infrastructure` - Cache layer testing
  - `rate-limiting` - Rate limiter functionality
  - `error-handling` - Error management testing

#### End-to-End Tests (`test-e2e.yml`)
- **Purpose**: Full workflow testing with external API simulation
- **Triggers**: Push, PR, Manual
- **Jobs**:
  - `mock-external-services` - External API mocking
  - `cli-integration` - Command-line interface testing
  - `export-workflows` - Export functionality testing
  - `error-scenarios` - Error condition handling

#### Test Matrix (`test-matrix.yml`)
- **Purpose**: Multi-dimensional testing across environments
- **Triggers**: Push, PR, Manual
- **Matrix Dimensions**:
  - Python versions: 3.11, 3.12
  - Operating systems: Ubuntu, macOS, Windows
  - Dependencies: minimal, full

#### Performance Tests (`test-performance.yml`)
- **Purpose**: Performance benchmarking and regression detection
- **Triggers**: Weekly schedule, Manual
- **Jobs**:
  - `benchmark-api` - API performance testing
  - `benchmark-calculations` - Mathematical operation benchmarks
  - `memory-profiling` - Memory usage analysis
  - `load-testing` - High-volume operation testing

### 🎯 Orchestration Workflows

#### Orchestrator (`orchestrator.yml`)
- **Purpose**: Intelligent coordination of test execution
- **Triggers**: Push, PR, Manual
- **Features**:
  - Dynamic strategy selection
  - Resource optimization
  - Test execution coordination
  - Failure analysis and reporting

#### Coordinator (`coordinator.yml`)
- **Purpose**: AI-powered work prioritization
- **Triggers**: Every 4 minutes (scheduled)
- **Features**:
  - Automated work queue management
  - Priority-based task scheduling
  - Resource allocation optimization
  - Progress tracking and reporting

#### AI Assessment (`github-ai-assessment.yml`)
- **Purpose**: Automated code analysis and backlog management
- **Triggers**: Hourly schedule, Manual
- **Features**:
  - Code quality assessment
  - Technical debt analysis
  - Automated issue creation
  - Performance trend analysis

### 🔧 Utility Workflows

#### Debug Logs (`debug-logs.yml`)
- **Purpose**: Debug and troubleshooting support
- **Triggers**: Manual with log level selection
- **Features**:
  - Configurable log levels
  - Log aggregation and analysis
  - Troubleshooting assistance

## Workflow Standards

### Naming Conventions
- **Files**: kebab-case (e.g., `test-unit.yml`)
- **Jobs**: descriptive names (e.g., `Unit - Calculations`)
- **Steps**: action-oriented (e.g., `Run unit tests`)

### Concurrency Controls
All workflows implement proper concurrency management:
```yaml
concurrency:
  group: workflow-name-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Security & Permissions
Minimal required permissions following security best practices:
```yaml
permissions:
  contents: read
  checks: write
```

### Performance Optimizations
- **Caching**: Poetry dependencies cached across runs
- **Timeouts**: Appropriate timeout limits (5-20 minutes)
- **Parallelization**: Jobs run in parallel where possible
- **Artifact Management**: 7-day retention for test results

## Integration with Development Workflow

### Makefile Integration
New Makefile targets for workflow management:
```bash
make workflows-status      # Check workflow status
make workflows-run WORKFLOW=ci  # Trigger specific workflow
make workflows-validate    # Validate workflow YAML
make workflows-ci          # Trigger CI workflow
make workflows-tests       # Trigger all test workflows
```

### Branch Protection
Recommended branch protection rules:
- Require `CI` workflow to pass
- Require `Unit Tests` workflow to pass
- Require up-to-date branches
- Require conversation resolution

### Development Process
1. **Feature Development**: Workflows trigger on feature branches
2. **Pull Request**: Comprehensive testing suite runs
3. **Code Review**: Workflow results inform review decisions
4. **Merge**: Production workflows validate final state
5. **Release**: Automated deployment and verification

## Monitoring & Observability

### Workflow Metrics
- Success/failure rates tracked
- Execution time monitoring
- Resource usage analysis
- Performance trend analysis

### Alerting
- Failed workflow notifications
- Performance degradation alerts
- Security scan alerts
- Deployment status notifications

### Troubleshooting
Common debugging approaches:
- Check workflow logs in GitHub Actions
- Use `make workflows-status` for current state
- Enable debug logging with environment variables
- Review artifact retention and download results

## Best Practices

### Development
1. **Test Locally**: Use `make check` before pushing
2. **Review Workflows**: Monitor workflow results
3. **Optimize Performance**: Profile slow tests
4. **Security First**: Follow security scanning recommendations

### Operations
1. **Monitor Trends**: Track performance over time
2. **Update Dependencies**: Keep actions up to date
3. **Review Permissions**: Regular security audits
4. **Backup Artifacts**: Preserve important test results

## Future Enhancements

### Planned Improvements
- Multi-cloud deployment support
- Advanced security scanning integration
- Performance regression detection
- Automated dependency updates
- Enhanced AI-powered analysis

### Integration Opportunities
- Slack/Teams notifications
- Advanced reporting dashboards
- Custom deployment strategies
- Enhanced monitoring integration