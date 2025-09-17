# GitHub Repository Settings for Praier

This document describes the recommended repository settings to ensure all PRs are properly tested before merging.

## Branch Protection Rules

To configure branch protection for the `main` branch that requires tests to pass:

### Via GitHub Web Interface

1. Go to **Settings** → **Branches**
2. Click **Add rule** for `main` branch
3. Configure the following settings:

**Protection Settings:**
- ✅ Require a pull request before merging
- ✅ Require approvals: 1
- ✅ Dismiss stale reviews when new commits are pushed
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Require linear history

**Required Status Checks:**
Add these required status checks:
- `test-status` (from `.github/workflows/tests.yml`)
- `test (3.11)` (recommended Python version)
- `security`
- `integration`

**Additional Settings:**
- ✅ Restrict pushes that create files that match a specific pattern (optional)
- ✅ Do not allow bypassing the above settings
- ✅ Allow force pushes: Disabled
- ✅ Allow deletions: Disabled

### Via GitHub CLI (Alternative)

```bash
# Enable branch protection with required status checks
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test-status","test (3.11)","security","integration"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null
```

## Workflow Permissions

Ensure the repository has the following workflow permissions:

**Settings** → **Actions** → **General**:
- Workflow permissions: **Read and write permissions**
- Allow GitHub Actions to create and approve pull requests: **Enabled**

## Repository Variables

Configure these repository variables for the monitoring workflow:

**Settings** → **Secrets and variables** → **Actions** → **Variables**:
- `PRAIER_REPOSITORIES`: Comma-separated list of repositories to monitor

## Security Settings

**Settings** → **Security & analysis**:
- ✅ Dependency graph
- ✅ Dependabot alerts
- ✅ Dependabot security updates
- ✅ Code scanning alerts (if using GitHub Advanced Security)
- ✅ Secret scanning alerts (if using GitHub Advanced Security)

## Result

With these settings:
1. **All PRs must pass tests** before they can be merged
2. **Code quality** is enforced through linting and formatting checks
3. **Security** is maintained through vulnerability scanning
4. **Branch history** remains clean and linear
5. **Reviews** are required from other contributors

The `test-status` job in the test workflow serves as the main gate - it only succeeds if all test suites (tests, security, integration) pass successfully.