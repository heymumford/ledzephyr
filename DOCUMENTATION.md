# LedZephyr Documentation

## What It Does
Calculates migration metrics for Zephyr Scale → qTest transitions.

## Quick Start

### 1. Install
```bash
pip install ledzephyr  # PyPI
# OR
git clone && poetry install  # Source
```

### 2. Configure
```bash
export LEDZEPHYR_JIRA_URL=https://your.atlassian.net
export LEDZEPHYR_JIRA_API_TOKEN=your_token
```

### 3. Run
```bash
lz metrics -p PROJECT -w 7d
```

## Architecture

```
Input → Pull → Calculate → Output
      ↓      ↓          ↓
   [APIs] [Metrics]  [JSON/CSV]
```

### Core Modules
- `metrics.py` - Calculations (adoption ratio, coverage parity)
- `client.py` - API interactions (Jira, Zephyr, qTest)
- `cache.py` - Request caching (TTL: 1 hour)

## Testing Strategy

### The Critical 5 (90% Risk Coverage)
```bash
make lean-test  # 530ms
```

| Test | Risk Mitigated | Time |
|------|----------------|------|
| Gold Master | Wrong calculations | 200ms |
| API Retry | Integration failures | 67ms |
| Date Boundaries | Time bugs | 13ms |
| Cache Expiry | Stale data | 50ms |
| Null Handling | Crashes | 200ms |

### Coverage: 53.60% (212 tests)
- `client.py`: 95% ✅
- `time_windows.py`: 100% ✅
- `metrics.py`: 50% 🟡

## API Reference

### CLI
```bash
lz doctor                    # Test connections
lz metrics -p PROJ -w 7d     # Get metrics
lz export --format csv       # Export data
```

### Python
```python
from ledzephyr import MetricsCalculator

calc = MetricsCalculator()
metrics = calc.calculate_project_metrics(
    test_cases, project_key="PROJ", time_window="7d"
)
```

### Metrics Calculated
- **adoption_ratio**: qtest_tests / total_tests
- **coverage_parity**: qtest_execution_rate / zephyr_execution_rate
- **active_users**: Unique assignees count
- **team_metrics**: Per-component breakdown

## Configuration

### Required
- `LEDZEPHYR_JIRA_URL`: Atlassian instance
- `LEDZEPHYR_JIRA_API_TOKEN`: Authentication

### Optional
- `LEDZEPHYR_TIMEOUT`: Request timeout (default: 30s)
- `LEDZEPHYR_MAX_RETRIES`: Retry attempts (default: 3)
- `LEDZEPHYR_CACHE_TTL`: Cache duration (default: 3600s)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Check API token |
| 429 Too Many Requests | Automatic retry with backoff |
| Wrong calculations | Verify gold master: `tests/integration/test_gold_master_algorithms.py` |
| Slow performance | Check cache: `~/.ledzephyr/cache/` |

## Development

### Setup
```bash
make init        # Install everything
make lean-test   # Run critical tests
make fix         # Auto-format code
```

### Adding Features
1. Write gold master test first
2. Implement minimum viable code
3. Run `make lean-test`
4. Add comprehensive tests only if needed

### Gold Master Datasets
```
testdata/fixtures/
├── math_input_*.json   # Test inputs
└── math_output_*.json  # Expected outputs
```

## Performance

- **Parsing**: 2.6μs per time window
- **API calls**: <100ms with retry
- **Full calculation**: <500ms for 1000 tests
- **Cache hit rate**: >90% in production

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim
COPY . /app
RUN pip install poetry && poetry install
CMD ["lz", "monitor", "--port", "8080"]
```

### Kubernetes
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ledzephyr-config
data:
  JIRA_URL: "https://your.atlassian.net"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ledzephyr
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: ledzephyr
        image: ledzephyr:latest
        envFrom:
        - configMapRef:
            name: ledzephyr-config
```

## Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Metrics (Prometheus)
```bash
curl http://localhost:8080/metrics
```

### Key Metrics
- `ledzephyr_api_requests_total`
- `ledzephyr_calculation_duration_seconds`
- `ledzephyr_cache_hit_ratio`

## Support

- **Issues**: https://github.com/heymumford/ledzephyr/issues
- **Tests**: 212 passing (53.60% coverage)
- **License**: MIT

---

**Philosophy**: Test what breaks. Document what matters. Ship what works.