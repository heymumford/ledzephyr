# GitHub Actions Secrets - Quick Reference

## 🚨 Required Secrets (Must Configure)

```
JIRA_TOKEN=your_jira_api_token_here
JIRA_URL=https://your-company.atlassian.net
JIRA_PROJECT_KEY=LEDZEPHYR
```

## ⚙️ Optional Secrets (For Full Integration Testing)

```
ZEPHYR_TOKEN=your_zephyr_api_token_here
QTEST_TOKEN=your_qtest_api_token_here
QTEST_URL=https://your-qtest-instance.qtestnet.com
```

## 🎯 Quick Setup

1. Go to **Repository Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each secret above
3. Paste the values for your environment

## ✅ Test Configuration

```bash
# Test Jira (required)
curl -H "Authorization: Bearer $JIRA_TOKEN" "$JIRA_URL/rest/api/2/myself"

# Test Zephyr (optional)
curl -H "Authorization: Bearer $ZEPHYR_TOKEN" "$JIRA_URL/rest/atm/1.0/healthcheck"

# Test qTest (optional)
curl -H "Authorization: bearer $QTEST_TOKEN" "$QTEST_URL/api/v3/users/me"
```

## 🔄 What Each Workflow Needs

| Workflow | Secrets Used | Purpose |
|----------|--------------|---------|
| `github-ai-assessment.yml` | JIRA_* (all) | Creates Jira tickets from AI recommendations |
| `coordinator-agent.yml` | GITHUB_TOKEN (automatic) | Orchestrates work every 4 minutes |
| `rail-3-external-integrations.yml` | All (optional for testing) | Tests external API integrations |
| `orchestrator-master.yml` | None | Coordinates parallel test rails |

**Note**: Without the required Jira secrets, AI assessment and automatic backlog management won't work, but all testing workflows will still function with mock services.