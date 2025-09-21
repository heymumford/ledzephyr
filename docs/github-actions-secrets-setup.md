# GitHub Actions Secrets Configuration

This document describes the GitHub Actions secrets configuration required for the LedZephyr parallel testing architecture to function properly.

## 🔐 Required Secrets

The following secrets must be configured in your GitHub repository settings under **Settings → Secrets and variables → Actions**.

### Core API Credentials

| Secret Name | Description | Required For | Example Value |
|-------------|-------------|--------------|---------------|
| `JIRA_TOKEN` | Jira API token for AI assessment integration | GitHub AI Assessment workflow | `ATATT3xFfGF0...` |
| `JIRA_URL` | Base URL for your Jira instance | GitHub AI Assessment workflow | `https://company.atlassian.net` |
| `JIRA_PROJECT_KEY` | Jira project key for automated ticket creation | GitHub AI Assessment workflow | `LEDZEPHYR` |

### Optional Service Tokens

| Secret Name | Description | Required For | Example Value |
|-------------|-------------|--------------|---------------|
| `ZEPHYR_TOKEN` | Zephyr Scale API token | External integrations testing | `eyJhbGciOiJIUzI1...` |
| `QTEST_TOKEN` | qTest API token | External integrations testing | `bearer_token_here` |
| `QTEST_URL` | qTest instance URL | External integrations testing | `https://company.qtestnet.com` |

## 🚀 Quick Setup Guide

### 1. Access Repository Secrets

1. Navigate to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click **Secrets and variables**
4. Click **Actions**

### 2. Add Required Secrets

Click **New repository secret** for each required secret:

#### Jira Configuration (Required)
```
Name: JIRA_TOKEN
Value: Your Jira API token (create at: https://id.atlassian.com/manage-profile/security/api-tokens)

Name: JIRA_URL
Value: https://your-company.atlassian.net

Name: JIRA_PROJECT_KEY
Value: LEDZEPHYR (or your project key)
```

#### Optional Service Tokens
```
Name: ZEPHYR_TOKEN
Value: Your Zephyr Scale API token

Name: QTEST_TOKEN
Value: Your qTest API token

Name: QTEST_URL
Value: https://your-qtest-instance.qtestnet.com
```

## 🔧 Workflow Usage

### GitHub AI Assessment Workflow

The `github-ai-assessment.yml` workflow uses these secrets:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Automatically provided
  JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}      # Required
  JIRA_URL: ${{ secrets.JIRA_URL }}          # Required
  JIRA_PROJECT_KEY: ${{ secrets.JIRA_PROJECT_KEY || 'LEDZEPHYR' }}
```

**What it does:**
- Runs hourly repository health assessments
- Creates Jira tickets from AI recommendations
- Generates priority-tagged improvement suggestions

### Coordinator Agent Workflow

The `coordinator-agent.yml` workflow uses:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Automatically provided
```

**What it does:**
- Runs every 4 minutes to coordinate work
- Analyzes repository state and prioritizes tasks
- Dispatches specialized agent personas

### Rail 3 External Integrations

The `rail-3-external-integrations.yml` workflow can use:

```yaml
env:
  JIRA_URL: ${{ secrets.JIRA_URL || 'http://localhost:8080' }}
  ZEPHYR_URL: ${{ secrets.ZEPHYR_URL || 'http://localhost:8081' }}
  QTEST_URL: ${{ secrets.QTEST_URL || 'http://localhost:8082' }}
```

**What it does:**
- Tests external API integrations with mock services
- Validates API client contract compliance
- Runs integration tests against simulated endpoints

## 🛡️ Security Best Practices

### Token Security

1. **Use API Tokens, Not Passwords**
   - Never store actual passwords in GitHub secrets
   - Use service-specific API tokens with minimal required permissions
   - Rotate tokens regularly (recommended: every 90 days)

2. **Principle of Least Privilege**
   - Grant only the minimum permissions needed
   - For Jira: Read access to projects, Write access to issues
   - For Zephyr/qTest: Read access to test cases and executions

3. **Token Validation**
   - Test tokens before adding them to GitHub secrets
   - Verify they work with your specific instance configurations

### Secret Management

1. **Environment-Specific Secrets**
   - Use different tokens for different environments
   - Consider separate Jira projects for CI/CD vs production

2. **Secret Rotation**
   - Set calendar reminders to rotate tokens
   - Update secrets immediately if compromised
   - Monitor token usage in service admin panels

3. **Access Control**
   - Limit repository access to authorized team members
   - Use GitHub teams for organized permission management
   - Enable branch protection rules

## 🔍 Troubleshooting

### Common Issues

#### 1. AI Assessment Workflow Fails
```
Error: Failed to create Jira ticket: Authentication failed
```

**Solution:**
- Verify `JIRA_TOKEN` is valid and not expired
- Check `JIRA_URL` format (should include https://)
- Ensure token has permission to create issues in the project

#### 2. Integration Tests Fail
```
Error: HTTP 401: Authentication failed
```

**Solution:**
- Check if optional service tokens are configured correctly
- Verify service URLs are accessible
- Confirm token permissions for test case access

#### 3. Coordinator Agent Issues
```
Error: Cannot dispatch workflows
```

**Solution:**
- Verify repository has Actions enabled
- Check workflow file syntax and permissions
- Ensure `GITHUB_TOKEN` has workflow dispatch permissions

### Validation Commands

Test your secret configuration:

```bash
# Test Jira connection
curl -H "Authorization: Bearer ${JIRA_TOKEN}" \
     "${JIRA_URL}/rest/api/2/myself"

# Test Zephyr connection (if configured)
curl -H "Authorization: Bearer ${ZEPHYR_TOKEN}" \
     "${JIRA_URL}/rest/atm/1.0/healthcheck"

# Test qTest connection (if configured)
curl -H "Authorization: bearer ${QTEST_TOKEN}" \
     "${QTEST_URL}/api/v3/users/me"
```

## 📋 Configuration Checklist

Use this checklist to verify your setup:

### Required Setup
- [ ] `JIRA_TOKEN` secret added
- [ ] `JIRA_URL` secret added
- [ ] `JIRA_PROJECT_KEY` secret added
- [ ] Jira token tested and working
- [ ] GitHub Actions enabled on repository

### Optional Setup
- [ ] `ZEPHYR_TOKEN` secret added (if using Zephyr Scale)
- [ ] `QTEST_TOKEN` secret added (if using qTest)
- [ ] `QTEST_URL` secret added (if using qTest)
- [ ] Service tokens tested and working

### Workflow Verification
- [ ] GitHub AI Assessment workflow can run manually
- [ ] Coordinator Agent workflow runs automatically every 4 minutes
- [ ] Rail 3 integration tests pass with mock services
- [ ] No authentication errors in workflow logs

## 🔄 Maintenance Schedule

### Weekly
- [ ] Review workflow execution logs for errors
- [ ] Check AI-generated Jira tickets for relevance

### Monthly
- [ ] Verify all secrets are still valid
- [ ] Review token usage in service admin panels
- [ ] Update token permissions if needed

### Quarterly
- [ ] Rotate all API tokens
- [ ] Review and update secret access permissions
- [ ] Audit workflow security configurations

## 📞 Support

### Getting Help

1. **Repository Issues**: Check GitHub workflow logs first
2. **Token Issues**: Verify in service admin panels
3. **Permission Issues**: Review token scopes and project access

### Useful Links

- [Jira API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Zephyr Scale API](https://support.smartbear.com/zephyr-scale-cloud/api-docs/)
- [qTest API Documentation](https://support.tricentis.com/community/manuals_detail.do?lang=en&version=Latest&module=qTest&url=qtest_api.htm)

---

*This documentation is automatically maintained as part of the LedZephyr parallel GitHub Actions architecture.*