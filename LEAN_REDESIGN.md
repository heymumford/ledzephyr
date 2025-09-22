# Lean Redesign - The 300 Line Solution

## Current Reality Check

We have **2,850 lines** for what should be a **~300 line problem**.

### What We Actually Need

```python
# ledzephyr.py - Complete solution in ~300 lines

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
import statistics

# 1. API Client (~50 lines)
def fetch_zephyr_data(project, token):
    """Fetch test data from Zephyr Scale."""
    url = f"https://api.zephyrscale.com/v2/testcases"
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(url, headers=headers, params={"projectKey": project})
    return response.json()

def fetch_qtest_data(project, token):
    """Fetch test data from qTest."""
    url = f"https://api.qtest.com/api/v3/projects/{project}/test-cases"
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(url, headers=headers)
    return response.json()

def fetch_jira_data(project, token):
    """Fetch project data from Jira."""
    url = f"https://api.atlassian.com/v2/projects/{project}"
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(url, headers=headers)
    return response.json()

# 2. Store timeseries (~50 lines)
def store_timeseries(data, source, project):
    """Store timestamped data to disk."""
    timestamp = datetime.now().isoformat()
    filepath = Path(f"data/{project}/{source}_{timestamp}.json")
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "source": source,
            "project": project,
            "data": data
        }, f)

    return filepath

def load_timeseries(project, source, days=30):
    """Load historical data."""
    cutoff = datetime.now() - timedelta(days=days)
    data_dir = Path(f"data/{project}")

    results = []
    for file in data_dir.glob(f"{source}_*.json"):
        with open(file) as f:
            data = json.load(f)
            if datetime.fromisoformat(data['timestamp']) > cutoff:
                results.append(data)

    return sorted(results, key=lambda x: x['timestamp'])

# 3. Calculate metrics (~50 lines)
def calculate_metrics(zephyr_data, qtest_data):
    """Calculate migration metrics."""
    zephyr_count = len(zephyr_data)
    qtest_count = len(qtest_data)
    total = zephyr_count + qtest_count

    if total == 0:
        return {"error": "No test data found"}

    adoption_rate = qtest_count / total if total > 0 else 0

    # Get execution counts from data
    zephyr_executions = sum(t.get('execution_count', 0) for t in zephyr_data)
    qtest_executions = sum(t.get('execution_count', 0) for t in qtest_data)

    return {
        "total_tests": total,
        "zephyr_tests": zephyr_count,
        "qtest_tests": qtest_count,
        "adoption_rate": adoption_rate,
        "zephyr_executions": zephyr_executions,
        "qtest_executions": qtest_executions,
        "migration_progress": f"{adoption_rate:.1%}"
    }

# 4. Analyze trends (~50 lines)
def analyze_trends(project, days=30):
    """Analyze historical trends."""
    zephyr_history = load_timeseries(project, 'zephyr', days)
    qtest_history = load_timeseries(project, 'qtest', days)

    if not zephyr_history and not qtest_history:
        return {"error": "No historical data"}

    # Calculate daily adoption rates
    adoption_trend = []
    for z, q in zip(zephyr_history, qtest_history):
        metrics = calculate_metrics(z['data'], q['data'])
        adoption_trend.append({
            'date': z['timestamp'][:10],
            'adoption_rate': metrics['adoption_rate']
        })

    # Calculate trend statistics
    rates = [d['adoption_rate'] for d in adoption_trend]
    if len(rates) > 1:
        trend_direction = "increasing" if rates[-1] > rates[0] else "decreasing"
        avg_rate = statistics.mean(rates)

        # Simple linear projection
        daily_change = (rates[-1] - rates[0]) / len(rates) if len(rates) > 1 else 0
        days_to_complete = int((1.0 - rates[-1]) / daily_change) if daily_change > 0 else None
    else:
        trend_direction = "insufficient data"
        avg_rate = rates[0] if rates else 0
        days_to_complete = None

    return {
        "trend_direction": trend_direction,
        "average_adoption": avg_rate,
        "current_adoption": rates[-1] if rates else 0,
        "days_to_complete": days_to_complete,
        "history": adoption_trend[-7:]  # Last 7 days
    }

# 5. Generate report (~50 lines)
def generate_report(project, metrics, trends):
    """Generate intelligent synthesis."""
    report = []
    report.append(f"# Migration Report: {project}")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    report.append("## Current State")
    report.append(f"- Total Tests: {metrics['total_tests']:,}")
    report.append(f"- Zephyr Scale: {metrics['zephyr_tests']:,}")
    report.append(f"- qTest: {metrics['qtest_tests']:,}")
    report.append(f"- Migration Progress: {metrics['migration_progress']}")

    report.append("\n## Execution Activity")
    report.append(f"- Zephyr Executions: {metrics['zephyr_executions']:,}")
    report.append(f"- qTest Executions: {metrics['qtest_executions']:,}")

    report.append("\n## Trend Analysis")
    report.append(f"- Direction: {trends['trend_direction']}")
    report.append(f"- Current Rate: {trends['current_adoption']:.1%}")
    report.append(f"- Average Rate: {trends['average_adoption']:.1%}")

    if trends['days_to_complete']:
        est_date = (datetime.now() + timedelta(days=trends['days_to_complete'])).strftime('%Y-%m-%d')
        report.append(f"- Estimated Completion: {est_date} ({trends['days_to_complete']} days)")

    report.append("\n## Recent History")
    for day in trends['history']:
        report.append(f"- {day['date']}: {day['adoption_rate']:.1%}")

    return "\n".join(report)

# 6. CLI (~50 lines)
import click

@click.command()
@click.option('--project', required=True, help='Jira project key')
@click.option('--days', default=30, help='Days of history to analyze')
@click.option('--fetch/--no-fetch', default=True, help='Fetch fresh data')
def main(project, days, fetch):
    """LedZephyr - Zephyr to qTest migration metrics."""

    # Load tokens from environment
    import os
    zephyr_token = os.getenv('ZEPHYR_TOKEN')
    qtest_token = os.getenv('QTEST_TOKEN')
    jira_token = os.getenv('JIRA_TOKEN')

    if fetch:
        # Fetch fresh data
        print(f"Fetching data for {project}...")
        zephyr_data = fetch_zephyr_data(project, zephyr_token)
        qtest_data = fetch_qtest_data(project, qtest_token)

        # Store timeseries
        store_timeseries(zephyr_data, 'zephyr', project)
        store_timeseries(qtest_data, 'qtest', project)
    else:
        # Load latest data
        zephyr_history = load_timeseries(project, 'zephyr', 1)
        qtest_history = load_timeseries(project, 'qtest', 1)

        if not zephyr_history or not qtest_history:
            print("No recent data found. Run with --fetch")
            return

        zephyr_data = zephyr_history[-1]['data']
        qtest_data = qtest_history[-1]['data']

    # Calculate metrics
    metrics = calculate_metrics(zephyr_data, qtest_data)

    # Analyze trends
    trends = analyze_trends(project, days)

    # Generate report
    report = generate_report(project, metrics, trends)

    print(report)

    # Save report
    report_path = Path(f"reports/{project}_{datetime.now().strftime('%Y%m%d')}.md")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")

if __name__ == '__main__':
    main()
```

## That's It!

The entire solution in **~300 lines**:
- Fetches from 3 APIs
- Stores timeseries data
- Calculates metrics
- Analyzes trends
- Generates reports

## What We DON'T Need

- ❌ 470 lines of rate_limiter.py
- ❌ 470 lines of observability.py
- ❌ 254 lines of monitoring_api.py
- ❌ Complex configuration system
- ❌ Circuit breakers
- ❌ Retry decorators
- ❌ Multiple export formats
- ❌ Abstract factories
- ❌ Dependency injection
- ❌ 13 separate files

## The Problem

We've been incrementally "improving" a massively overengineered system instead of starting fresh with the actual requirements.

## The Solution

Delete everything and write the 300-line version that actually solves the problem.