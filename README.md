# ledzephyr

Migration metrics for Zephyr Scale → qTest.

[![Coverage](https://img.shields.io/badge/coverage-53.60%25-yellow.svg)](htmlcov/index.html)
[![Tests](https://img.shields.io/badge/tests-212-brightgreen.svg)](tests/)

## Quick Start

```bash
# Install
pip install ledzephyr

# Configure (.env file)
LEDZEPHYR_JIRA_URL=https://your.atlassian.net
LEDZEPHYR_JIRA_API_TOKEN=your_token

# Run
lz metrics -p PROJECT -w 7d
```

## The Critical 5 Tests

```bash
make lean-test  # 530ms, covers 90% of risks
```

## Documentation

See [DOCUMENTATION.md](DOCUMENTATION.md) for:
- Architecture
- API Reference
- Configuration
- Troubleshooting
- Development

## License

MIT