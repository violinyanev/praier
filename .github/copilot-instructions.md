# Praier - GitHub PR Monitoring Tool

Praier is a Python tool that automates GitHub pull request workflows with Actions auto-approval and Copilot integration. It monitors PRs across multiple GitHub servers and automatically approves workflow runs and requests Copilot fixes for failing checks.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Install
- Install Python package with dev dependencies:
  - `pip install -e ".[dev]"` -- takes 10-15 seconds normally. NEVER CANCEL. Set timeout to 120+ seconds.
  - **NOTE: In environments with limited network connectivity, installation may fail with SSL/timeout errors**
- Basic package install (without dev tools):
  - `pip install -e .`

### Development Workflow
- **ALWAYS run linting and formatting before committing changes:**
  - `black praier/` -- formats Python code, takes ~0.3 seconds
  - `isort praier/` -- sorts imports, takes ~0.1 seconds  
  - `flake8 praier/` -- lints code (NOTE: currently has many style issues, focus on new code)
  - `mypy praier/` -- type checking (NOTE: currently has type errors, focus on new code)
- Run tests: `pytest` -- takes ~0.35 seconds, all 8 tests should pass. NEVER CANCEL.
- **Run tests after any code changes** to ensure functionality works.

### CLI Usage and Testing
- Test CLI help: `praier --help`
- Check status: `praier status` 
- Generate sample config: `praier generate-config --output /tmp/test-config.yaml`
- Test with minimal config: `GITHUB_TOKEN=fake_token PRAIER_REPOSITORIES=test/repo praier status`
- Run demo: `python demo.py` -- takes ~10 seconds, shows mock monitoring functionality

### Functional Testing
- **ALWAYS test CLI commands after making changes to CLI module**
- **ALWAYS run the demo script after making changes to core monitoring logic**
- Test configuration loading with both environment variables and YAML files
- Verify error handling by testing with invalid configurations

## Validation Scenarios

After making any changes, **ALWAYS** run these validation steps:

### Basic Functionality Test
1. `pip install -e ".[dev]"` -- ensure installation works
2. `praier --help` -- verify CLI loads without errors
3. `pytest` -- all tests must pass
4. `python demo.py` -- verify core functionality simulation works

### Development Workflow Validation
1. `black praier/` -- format code
2. `isort praier/` -- sort imports
3. `pytest` -- ensure tests still pass after formatting
4. `praier status` -- verify CLI functionality after formatting

### Configuration Testing
1. `praier generate-config --output /tmp/test-config.yaml` -- test config generation
2. `GITHUB_TOKEN=fake_token PRAIER_REPOSITORIES=test/repo praier status` -- test env var config
3. `praier --config /tmp/test-config.yaml status` -- test YAML config loading

## Build and Deployment

### Docker (Limited)
- Docker build: `docker build -t praier .` 
- **NOTE: Docker build currently fails due to SSL certificate issues in this environment**
- Expected build time: ~2-3 minutes when working
- In production environments, Docker build should work normally

### System Installation (Linux)
- Use installation script: `sudo scripts/install.sh`
- Creates systemd service at `/etc/systemd/system/praier.service`
- Installs to `/opt/praier` with dedicated user account

## Common Commands Reference

### Timing Expectations - NEVER CANCEL
- Package installation: 10-15 seconds normally (use 120+ second timeout, may fail in limited connectivity environments)
- Tests: ~0.32 seconds (use 60+ second timeout for safety)  
- Demo script: ~10 seconds (use 60+ second timeout)
- Linting/formatting: 0.1-0.3 seconds each (use 30+ second timeout for safety)
- Full development workflow (black + isort + pytest + cli test): ~0.75 seconds
- Docker build: 2-3 minutes when working (use 10+ minute timeout, currently fails with SSL issues)

### Quick File Locations
```
Repository root: /home/runner/work/praier/praier/
├── praier/           # Main Python package
├── tests/            # Test files (8 tests)
├── scripts/          # Installation scripts
├── .github/workflows/# GitHub Actions
├── pyproject.toml    # Package configuration
├── demo.py           # Functional demo script
├── Dockerfile        # Container build (has SSL issues)
└── README.md         # Comprehensive documentation
```

### Key Package Modules
- `praier/cli.py` - Command-line interface (main entry point)
- `praier/config.py` - Configuration management (env vars + YAML)
- `praier/github_client.py` - GitHub API integration
- `praier/monitor.py` - Core monitoring logic
- `praier/__init__.py` - Package initialization

### Environment Variables (for testing)
```bash
# Minimal working config for testing
export GITHUB_TOKEN=your_token_here
export PRAIER_REPOSITORIES=owner/repo1,owner/repo2

# Additional options
export PRAIER_POLL_INTERVAL=60
export PRAIER_AUTO_APPROVE=true  
export PRAIER_AUTO_FIX=true
export PRAIER_LOG_LEVEL=INFO
```

## Known Issues and Limitations
- **Docker build fails with SSL certificate verification errors in this environment** - document this if encountered
- **Existing code has linting issues** - focus on making new code clean rather than fixing all existing issues
- **MyPy type checking has errors** - focus on new code having proper types
- **Flake8 has many style warnings** - focus on new code following style guidelines

## Git and CI Integration
- GitHub Actions workflow runs every 30 minutes: `.github/workflows/praier-monitor.yml`
- The workflow installs package and runs `praier monitor` for 5 minutes
- Always test changes to CLI or core logic before committing
- **CRITICAL: Always run `black praier/ && isort praier/ && pytest` before committing**

This is a mature Python project with working CI/CD. Focus on making minimal changes and ensuring all validation steps pass.