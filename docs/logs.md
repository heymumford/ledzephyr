# Log Viewing with lnav

## Overview

The `dev/logs` CLI provides real-time log viewing, merging, filtering, and SQL querying for parallel worker logs using [lnav](https://lnav.org/), a powerful log file navigator.

## Quick Start

```bash
# Install dependencies
make deps-logs

# View all service logs
dev/logs --all

# View specific service logs
dev/logs --svc workerA --svc workerB

# Filter for specific messages
dev/logs --all --grep "Retrying"

# Query logs with SQL
dev/logs --query "select level, count(*) from logs group by level"
```

## Installation

### macOS (via Homebrew)
```bash
brew install lnav
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-get install lnav

# Fedora/RHEL
sudo dnf install lnav
```

## Log Format

Logs must be in JSON Lines format (`.log.jsonl`) with the following structure:

```json
{
  "ts": "2025-09-21T10:30:45.123456Z",  // UTC ISO-8601 timestamp (required)
  "level": "info",                        // RFC 5424 level (required)
  "msg": "Processing item",                // Log message (required)
  "svc": "workerA",                       // Service name (required)
  "pid": 1234,                            // Process ID (required)
  "tid": "thread-1",                      // Thread ID (required)
  "trace_id": "abcd...ef",                // OpenTelemetry trace ID (optional)
  "span_id": "0123...ef",                 // OpenTelemetry span ID (optional)
  "elapsed_ms": 125.5                     // Elapsed time in ms (optional)
}
```

### Severity Levels (RFC 5424)
- `debug`: Debug-level messages
- `info`: Informational messages
- `notice`: Normal but significant conditions
- `warning`: Warning conditions
- `err`: Error conditions
- `crit`: Critical conditions
- `alert`: Action must be taken immediately
- `emerg`: System is unusable

## CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--all` | View logs from all services | `dev/logs --all` |
| `--svc <name>` | View logs from specific service(s) | `dev/logs --svc workerA --svc workerB` |
| `--since <ISO8601>` | Show logs since timestamp | `dev/logs --since 2025-09-21T10:00:00Z` |
| `--grep <regex>` | Filter logs matching pattern | `dev/logs --grep "error\|fail"` |
| `--query <SQL>` | Execute SQL query and exit | `dev/logs --query "select * from logs"` |
| `--help` | Show usage information | `dev/logs --help` |

## Common SQL Queries

### Count by log level
```sql
dev/logs --query "select level, count(*) as count from logs group by level order by count desc"
```

### Find errors in last hour
```sql
dev/logs --query "select ts, svc, msg from logs where level = 'err' and ts > datetime('now', '-1 hour')"
```

### Service performance metrics
```sql
dev/logs --query "select svc, avg(elapsed_ms) as avg_ms, max(elapsed_ms) as max_ms from logs where elapsed_ms is not null group by svc"
```

### Trace ID lookup
```sql
dev/logs --query "select ts, svc, msg from logs where trace_id = 'abcdef0123456789abcdef0123456789'"
```

### Top 10 slowest operations
```sql
dev/logs --query "select ts, svc, msg, elapsed_ms from logs where elapsed_ms is not null order by elapsed_ms desc limit 10"
```

## Interactive Mode Commands

When in lnav's interactive mode:

| Key | Action |
|-----|--------|
| `q` | Quit |
| `?` | Show help |
| `/` | Search forward |
| `n` | Next search result |
| `N` | Previous search result |
| `f` | Follow mode (tail -f) |
| `TAB` | Switch between log/SQL views |
| `:` | Enter command mode |
| `;` | Enter SQL mode |

### Useful lnav Commands
- `:filter-in <regex>` - Show only matching lines
- `:filter-out <regex>` - Hide matching lines
- `:reset-filters` - Clear all filters
- `:goto <time>` - Jump to timestamp
- `:save-to <file>` - Save filtered logs
- `:switch-to-view log` - Switch to log view
- `:switch-to-view sql` - Switch to SQL result view

## Configuration

### Log Directory
By default, logs are read from `./var/log/<service>/*.log.jsonl`. Override with:
```bash
LOG_DIR=/custom/path dev/logs --all
```

### Custom Formats
Log format definitions are in `tools/lnav/formats/app-format.json`. The format includes:
- Timestamp parsing
- Level-to-severity mapping
- Field extraction
- Syntax highlighting

### lnav Configuration
Global lnav settings are in `tools/lnav/lnav_config.json`:
- Default view settings
- SQL output configuration
- Archive management

## Troubleshooting

### No logs found
```bash
Error: no logs found in ./var/log
```
**Solution**: Ensure services are running and logging to the correct directory.

### lnav not installed
```bash
Error: lnav is not installed
```
**Solution**: Run `make deps-logs` or install manually.

### Invalid timestamp format
```bash
Line 1: Invalid timestamp format (not UTC ISO-8601)
```
**Solution**: Ensure timestamps are in format `YYYY-MM-DDTHH:MM:SS.ffffffZ`.

### Permission denied
```bash
Permission denied: ./var/log/service/app.log.jsonl
```
**Solution**: Check file permissions with `ls -la ./var/log/`.

## Testing

Run all log-related tests:
```bash
make test-logs
```

Validate log format schemas:
```bash
make lint-logs
```

## Integration with Services

### Python Logging Example
```python
import json
import logging
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "svc": "myservice",
            "pid": os.getpid(),
            "tid": threading.current_thread().name
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger()
logger.addHandler(handler)
```

### Node.js Example
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(info => JSON.stringify({
      ts: new Date().toISOString(),
      level: info.level,
      msg: info.message,
      svc: 'myservice',
      pid: process.pid,
      tid: require('worker_threads').threadId
    }))
  ),
  transports: [
    new winston.transports.File({
      filename: './var/log/myservice/app.log.jsonl'
    })
  ]
});
```

## Best Practices

1. **Use structured logging**: Always log in JSON format for easy parsing
2. **Include trace IDs**: Add OpenTelemetry trace/span IDs for distributed tracing
3. **Log at appropriate levels**: Use debug for development, info for production
4. **Include timing**: Add `elapsed_ms` for performance-critical operations
5. **Rotate logs**: Implement log rotation to prevent disk space issues
6. **UTC timestamps**: Always use UTC to avoid timezone confusion

## Further Reading

- [lnav Documentation](https://docs.lnav.org/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/reference/specification/trace/semantic_conventions/)
- [RFC 5424 - Syslog Protocol](https://tools.ietf.org/html/rfc5424)
- [12-Factor App: Logs](https://12factor.net/logs)