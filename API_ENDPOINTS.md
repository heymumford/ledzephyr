# Essential API Endpoints for LedZephyr

## Overview
Out of thousands of available API endpoints, we only need ~15 total endpoints across three APIs to accomplish our goal of tracking Zephyr Scale → qTest migration metrics.

## 1. Jira Cloud API

**OpenAPI Spec**: https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json

### Essential Endpoints (4)

```python
# 1. Search for active projects
GET /rest/api/3/project/search
params: {
    "expand": "insight",
    "orderBy": "lastIssueUpdatedTime",
    "query": "",  # Optional search term
    "status": "live"
}

# 2. Get project details
GET /rest/api/3/project/{projectIdOrKey}

# 3. Search for issues/defects (JQL)
GET /rest/api/3/search
params: {
    "jql": "project = {project} AND updated >= -6m AND issuetype in (Bug, Defect)",
    "fields": "summary,status,created,updated,assignee",
    "maxResults": 100
}

# 4. Get issue details (for linked defects)
GET /rest/api/3/issue/{issueIdOrKey}
```

## 2. Zephyr Scale API (SmartBear)

**Documentation**: https://support.smartbear.com/zephyr-scale-cloud/api-docs/

### Essential Endpoints (5)

```python
# 1. Search test cases (with 6-month filter)
GET /rest/atm/1.0/testcase/search
params: {
    "query": 'projectKey = "{project}" AND updatedDate >= now(-6m)',
    "maxResults": 1000,
    "fields": "key,name,status,createdOn,updatedOn,owner"
}

# 2. Get test executions
GET /rest/atm/1.0/testrun/search
params: {
    "query": 'projectKey = "{project}" AND executedOn >= now(-6m)',
    "maxResults": 1000
}

# 3. Get test execution results
GET /rest/atm/1.0/testexecution/{testExecutionId}

# 4. Get linked defects for test case
GET /rest/atm/1.0/testcase/{testCaseKey}/links
params: {
    "linkType": "defect"
}

# 5. Get test cycle data
GET /rest/atm/1.0/testcycle/search
params: {
    "query": 'projectKey = "{project}"',
    "maxResults": 100
}
```

## 3. qTest API (Tricentis)

**Base URL**: https://{site}.qtestnet.com/api/v3

### Essential Endpoints (6)

```python
# 1. Authenticate
POST /api/v3/login
body: {
    "grant_type": "password",
    "username": "{username}",
    "password": "{token}"
}

# 2. List projects
GET /api/v3/projects

# 3. Get test cases
GET /api/v3/projects/{projectId}/test-cases
params: {
    "pageSize": 999,
    "includeTotalCount": true,
    "lastModifiedStartDate": "{6_months_ago}",
    "expandProps": "true"
}

# 4. Get test runs
GET /api/v3/projects/{projectId}/test-runs
params: {
    "pageSize": 999,
    "lastModifiedStartDate": "{6_months_ago}"
}

# 5. Get test execution logs
GET /api/v3/projects/{projectId}/test-logs
params: {
    "pageSize": 999,
    "executedStartDate": "{6_months_ago}"
}

# 6. Get defects
GET /api/v3/projects/{projectId}/defects
params: {
    "pageSize": 999,
    "lastModifiedStartDate": "{6_months_ago}"
}
```

## Implementation Notes

### Date Filtering
- **Last 6 months**: Focus only on active data
- **Jira JQL**: `updated >= -6m`
- **Zephyr**: `updatedDate >= now(-6m)`
- **qTest**: Use ISO date 6 months ago

### Response Fields We Care About
```python
# Minimal fields needed for metrics
test_case = {
    "id": str,
    "created": datetime,
    "updated": datetime,
    "status": str,
    "owner": str,
    "execution_count": int
}

# For trend analysis
activity = {
    "date": datetime,
    "user": str,
    "action": str,  # created, executed, updated
    "platform": str  # zephyr or qtest
}
```

### Rate Limiting
- Jira: 100 requests per 10 seconds
- Zephyr Scale: 100 requests per minute
- qTest: 60 requests per minute

### Authentication
- **Jira/Zephyr**: Bearer token (API key)
- **qTest**: Login endpoint returns session token

## Total API Surface

**15 endpoints** out of thousands available:
- 4 from Jira Cloud
- 5 from Zephyr Scale
- 6 from qTest

This minimal set provides everything needed for:
- Migration metrics calculation
- Trend analysis
- Activity tracking
- Completion date estimation