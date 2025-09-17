# Praier

A tool to automate pull request workflows with GitHub Actions and Copilot integration.

## Overview

Praier is a Python tool that monitors GitHub pull requests across one or more GitHub servers and automatically:

- **Approves GitHub Actions workflows** that are waiting for approval
- **Requests GitHub Copilot fixes** for failing checks in pull requests
- **Monitors PR status changes** using GraphQL queries with efficient change detection
- **Runs as a background service** with configurable polling intervals

## Features

- 🔄 **Multi-server support**: Connect to public GitHub and GitHub Enterprise Server instances
- 🚀 **Auto-approve Actions**: Automatically approve workflow runs that require manual approval
- 🤖 **Copilot integration**: Request GitHub Copilot to fix failing checks in PRs
- 📊 **GraphQL monitoring**: Efficient PR monitoring using GitHub's GraphQL API
- ⚙️ **Configurable**: Flexible configuration via environment variables or YAML files
- 🔍 **Change detection**: Only takes action when PR status actually changes
- 📝 **Comprehensive logging**: Detailed logging for monitoring and debugging

## Installation

```bash
# Clone the repository
git clone https://github.com/violinyanev/praier.git
cd praier

# Install the package
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

1. **Set up your GitHub token**:
   ```bash
   export GITHUB_TOKEN=your_github_token_here
   export PRAIER_REPOSITORIES=owner/repo1,owner/repo2
   ```

2. **Test the connection**:
   ```bash
   praier test-connection owner/repo1
   ```

3. **Start monitoring**:
   ```bash
   praier monitor
   ```

## Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
# GitHub token for the default (public) GitHub instance
GITHUB_TOKEN=your_github_token_here

# Repositories to monitor (comma-separated)
PRAIER_REPOSITORIES=owner/repo1,owner/repo2

# Monitoring settings
PRAIER_POLL_INTERVAL=60
PRAIER_AUTO_APPROVE=true
PRAIER_AUTO_FIX=true
PRAIER_LOG_LEVEL=INFO
```

### YAML Configuration

Create a `config.yaml` file (copy from `config.example.yaml`):

```yaml
github_servers:
  - name: "public"
    url: "https://api.github.com"
    token: "${GITHUB_TOKEN}"

monitoring:
  poll_interval: 60
  repositories:
    - "owner/repo1"
    - "owner/repo2"
  auto_approve_actions: true
  auto_fix_with_copilot: true

log_level: "INFO"
```

## Usage

### Commands

```bash
# Start monitoring (main command)
praier monitor

# Check configuration status
praier status

# Test connection to a repository
praier test-connection owner/repo

# Generate sample configuration
praier generate-config --output config.yaml

# Use custom configuration file
praier --config config.yaml monitor

# Set log level
praier --log-level DEBUG monitor
```

### Multiple GitHub Servers

To monitor repositories across multiple GitHub instances:

```bash
# Environment variables approach
export PRAIER_SERVER_COUNT=2
export GITHUB_TOKEN=public_github_token
export GITHUB_1_NAME=enterprise
export GITHUB_1_URL=https://github.company.com/api/v3
export GITHUB_1_TOKEN=enterprise_github_token
```

Or use YAML configuration:

```yaml
github_servers:
  - name: "public"
    url: "https://api.github.com"
    token: "${GITHUB_TOKEN}"
  - name: "enterprise"
    url: "https://github.company.com/api/v3"
    token: "${GITHUB_ENTERPRISE_TOKEN}"
```

## How It Works

1. **Monitoring Loop**: Praier runs a continuous monitoring loop that polls GitHub APIs at configurable intervals
2. **Change Detection**: Uses GraphQL to efficiently fetch PR data and detect changes
3. **Auto-Approval**: When workflow runs are detected with "queued" or "waiting" status, automatically approves them
4. **Copilot Integration**: When check runs fail, creates a comment mentioning @copilot with details about the failures
5. **State Tracking**: Maintains state for each PR to avoid duplicate actions

## GitHub Token Permissions

Your GitHub token needs the following permissions:

- `repo` - Full repository access (to read PRs, workflow runs, and create comments)
- `actions:read` - Read access to Actions workflows
- `actions:write` - Write access to approve workflow runs
- `pull_requests:write` - Write access to create comments on PRs

For GitHub Apps, ensure similar permissions are granted.

## Security Considerations

- Store GitHub tokens securely (use environment variables or secure configuration management)
- Consider using GitHub Apps with minimal required permissions instead of personal access tokens
- Monitor logs for any unauthorized access attempts
- Regularly rotate your GitHub tokens

## GitHub Actions Workflow

This repository includes a GitHub Actions workflow that automatically runs the Praier monitor every 30 minutes.

### Workflow Configuration

The workflow (`.github/workflows/praier-monitor.yml`) is configured to:

- **Schedule**: Runs every 30 minutes using cron schedule `*/30 * * * *`
- **Manual trigger**: Can be triggered manually via GitHub Actions UI
- **Environment**: Uses Ubuntu latest with Python 3.11
- **Timeout**: Limited to 5 minutes (300 seconds) per run

### Required Configuration

To use the workflow, configure these repository settings:

1. **Repository Variables** (Settings → Secrets and variables → Actions → Variables):
   - `PRAIER_REPOSITORIES`: Comma-separated list of repositories to monitor (e.g., `owner/repo1,owner/repo2`)

2. **Repository Secrets** (automatically available):
   - `GITHUB_TOKEN`: Automatically provided by GitHub Actions with appropriate permissions

### Workflow Environment Variables

The workflow sets these environment variables:
- `PRAIER_POLL_INTERVAL`: 1800 seconds (30 minutes)
- `PRAIER_AUTO_APPROVE`: true (auto-approve workflow runs)
- `PRAIER_AUTO_FIX`: true (request Copilot fixes for failures)
- `PRAIER_LOG_LEVEL`: INFO

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=praier --cov-report=html

# Format code
black praier/
isort praier/

# Type checking
mypy praier/

# Lint
flake8 praier/
```

### Running Tests

Praier includes a comprehensive test suite with 60+ tests covering:

- **CLI functionality**: All command-line commands and options
- **Monitor logic**: Async PR monitoring, workflow approval, Copilot integration
- **Script validation**: Installation scripts, systemd service configuration
- **Integration tests**: End-to-end functionality validation

```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_cli.py -v
pytest tests/test_monitor.py -v
pytest tests/test_scripts.py -v

# Run tests with coverage report
pytest tests/ --cov=praier --cov-report=term-missing

# Run tests for specific functionality
pytest tests/ -k "test_monitor_command"
```

### Continuous Integration

The project uses GitHub Actions for continuous integration:

- **Test Workflow** (`.github/workflows/tests.yml`): Runs on all PRs and pushes
  - Tests across Python 3.8-3.12
  - Code quality checks (flake8, mypy, black, isort)
  - Security scanning (bandit, safety)
  - Coverage reporting
  - Integration testing

- **Monitor Workflow** (`.github/workflows/praier-monitor.yml`): Production monitoring
  - Runs tests before deploying
  - Only proceeds if tests pass
  - Executes actual monitoring if tests succeed

**Pull Request Requirements**: All PRs must pass the complete test suite before merging. The test workflow is configured as a required status check.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the development tools (black, isort, mypy, flake8)
6. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
