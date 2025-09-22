# GitHub Workflows - Lean CI

## Single Workflow Philosophy

We maintain **one simple workflow** for our 306-line codebase:

### `lean-ci.yml`
- Runs tests
- Checks formatting
- Performs linting
- Verifies code stays under 350 lines

## Why Just One Workflow?

The entire application is 306 lines. We don't need:
- ❌ 11 different test workflows
- ❌ Complex orchestration
- ❌ AI-powered coordination
- ❌ Performance benchmarks
- ❌ Matrix testing

## Local Development

```bash
# Run tests
make test

# Format code
make format

# Lint
make lint

# Check line count
make info
```

## Future Automation

When ready, we'll integrate with **Atlassian Rovo AI** for intelligent automation, not complex GitHub workflows.