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

### Quick Reference
- [Local Development Guide](DOCUMENTATION.md)
- [AI Assistant Instructions](CLAUDE.md)

### Project Management
- [Confluence Space](https://balabushka.atlassian.net/wiki/spaces/LedZephyr/overview) - Architecture, philosophy, and guides
- [Jira Project (LED)](https://balabushka.atlassian.net/browse/LED) - Work tracking and roadmap

### Key Resources
- **Mission Control**: Strategic documentation and lean philosophy
- **Technical Vault**: Architecture and implementation details
- **Epic LED-46**: Adoption Intelligence System implementation

## License

MIT