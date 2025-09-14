"""
Tests for installation scripts and other scripts functionality.
"""

import os
import subprocess
from unittest.mock import patch

import pytest


class TestInstallScript:
    """Test class for install.sh script validation."""

    def test_install_script_exists(self):
        """Test that the install script exists and is readable."""
        script_path = "/home/runner/work/praier/praier/scripts/install.sh"
        assert os.path.exists(script_path)
        assert os.access(script_path, os.R_OK)

    def test_install_script_has_shebang(self):
        """Test that the install script has proper shebang."""
        script_path = "/home/runner/work/praier/praier/scripts/install.sh"
        with open(script_path, "r") as f:
            first_line = f.readline().strip()
            assert first_line == "#!/bin/bash"

    def test_install_script_syntax(self):
        """Test that the install script has valid bash syntax."""
        script_path = "/home/runner/work/praier/praier/scripts/install.sh"

        # Use bash -n to check syntax without executing
        result = subprocess.run(
            ["bash", "-n", script_path], capture_output=True, text=True
        )

        assert result.returncode == 0, f"Script syntax error: {result.stderr}"

    def test_install_script_content_validation(self):
        """Test that the install script contains expected commands."""
        script_path = "/home/runner/work/praier/praier/scripts/install.sh"

        with open(script_path, "r") as f:
            content = f.read()

        # Check for critical installation steps
        expected_patterns = [
            "set -e",  # Fail on any error
            "useradd",  # Create user
            "mkdir -p",  # Create directories
            "python3 -m venv",  # Create virtual environment
            "pip install",  # Install package
            "systemctl",  # Systemd operations
        ]

        for pattern in expected_patterns:
            assert pattern in content, f"Missing expected pattern: {pattern}"

    def test_install_script_security_checks(self):
        """Test that the install script has basic security checks."""
        script_path = "/home/runner/work/praier/praier/scripts/install.sh"

        with open(script_path, "r") as f:
            content = f.read()

        # Should check for root privileges
        assert (
            "EUID" in content or "$(id -u)" in content
        ), "Script should check for root privileges"

        # Should have error handling
        assert "set -e" in content, "Script should use 'set -e' for error handling"


class TestSystemdService:
    """Test class for systemd service file validation."""

    def test_service_file_exists(self):
        """Test that the service file exists and is readable."""
        service_path = "/home/runner/work/praier/praier/scripts/praier.service"
        assert os.path.exists(service_path)
        assert os.access(service_path, os.R_OK)

    def test_service_file_content(self):
        """Test that the service file has proper systemd structure."""
        service_path = "/home/runner/work/praier/praier/scripts/praier.service"

        with open(service_path, "r") as f:
            content = f.read()

        # Check for required systemd sections
        required_sections = ["[Unit]", "[Service]", "[Install]"]
        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

        # Check for required service properties
        required_properties = [
            "Description=",
            "ExecStart=",
            "User=",
            "WorkingDirectory=",
            "Restart=",
        ]

        for prop in required_properties:
            assert prop in content, f"Missing required property: {prop}"

    def test_service_security_settings(self):
        """Test that the service file has security hardening."""
        service_path = "/home/runner/work/praier/praier/scripts/praier.service"

        with open(service_path, "r") as f:
            content = f.read()

        # Check for security settings
        security_settings = [
            "NoNewPrivileges=true",
            "PrivateTmp=true",
            "ProtectSystem=",
            "ProtectHome=",
        ]

        for setting in security_settings:
            assert setting in content, f"Missing security setting: {setting}"

    def test_service_environment_variables(self):
        """Test that the service file defines necessary environment variables."""
        service_path = "/home/runner/work/praier/praier/scripts/praier.service"

        with open(service_path, "r") as f:
            content = f.read()

        # Check for required environment variables
        env_vars = [
            "GITHUB_TOKEN=",
            "PRAIER_REPOSITORIES=",
            "PRAIER_POLL_INTERVAL=",
            "PRAIER_LOG_LEVEL=",
        ]

        for env_var in env_vars:
            assert env_var in content, f"Missing environment variable: {env_var}"


class TestDemoScript:
    """Test class for demo.py script functionality."""

    def test_demo_script_exists(self):
        """Test that the demo script exists and is readable."""
        demo_path = "/home/runner/work/praier/praier/demo.py"
        assert os.path.exists(demo_path)
        assert os.access(demo_path, os.R_OK)

    def test_demo_script_syntax(self):
        """Test that the demo script has valid Python syntax."""
        demo_path = "/home/runner/work/praier/praier/demo.py"

        # Compile the script to check syntax
        with open(demo_path, "r") as f:
            source = f.read()

        try:
            compile(source, demo_path, "exec")
        except SyntaxError as e:
            pytest.fail(f"Demo script has syntax error: {e}")

    @patch("praier.monitor.PRMonitor")
    @pytest.mark.asyncio
    async def test_demo_script_mock_functionality(self, mock_pr_monitor):
        """Test demo script mock functionality without actually running it."""
        # Import the demo module
        import sys

        sys.path.insert(0, "/home/runner/work/praier/praier")

        from demo import MockGitHubClient

        # Test MockGitHubClient
        mock_client = MockGitHubClient()

        # Test mock methods
        prs = mock_client.get_pull_requests("test/repo")
        assert len(prs) == 1
        assert prs[0].number == 123

        workflow_runs = mock_client.get_workflow_runs("test/repo")
        assert len(workflow_runs) == 1
        assert workflow_runs[0].status == "queued"

        check_runs = mock_client.get_check_runs("test/repo", "abc123")
        assert len(check_runs) == 2
        assert all(check.conclusion == "failure" for check in check_runs)

        # Test approval and fix request methods
        assert mock_client.approve_workflow_run("test/repo", "run-123") is True
        assert "run-123" in mock_client.approved_runs

        assert mock_client.request_copilot_fix("test/repo", 123, check_runs) is True
        assert 123 in mock_client.copilot_requests

    def test_demo_imports(self):
        """Test that demo script can import all required modules."""
        # Try to import the demo module to check for import errors
        import sys

        sys.path.insert(0, "/home/runner/work/praier/praier")

        try:
            import demo

            # Check that key classes are available
            assert hasattr(demo, "MockGitHubClient")
            assert hasattr(demo, "demo_monitoring")
        except ImportError as e:
            pytest.fail(f"Demo script import failed: {e}")


class TestScriptIntegration:
    """Test class for integration between scripts."""

    def test_praier_command_available(self):
        """Test that praier command is available after installation."""
        # This would typically be tested in a full integration environment
        # For now, just verify the entry point is defined
        import pkg_resources

        # Check if praier entry point is defined
        entry_points = list(
            pkg_resources.iter_entry_points("console_scripts", "praier")
        )
        assert len(entry_points) > 0, "praier console script entry point not found"

    def test_package_structure(self):
        """Test that the package has the expected structure."""
        package_dir = "/home/runner/work/praier/praier/praier"

        expected_files = [
            "__init__.py",
            "cli.py",
            "config.py",
            "github_client.py",
            "monitor.py",
        ]

        for filename in expected_files:
            file_path = os.path.join(package_dir, filename)
            assert os.path.exists(file_path), f"Missing package file: {filename}"

    def test_project_metadata(self):
        """Test that project metadata is properly defined."""
        pyproject_path = "/home/runner/work/praier/praier/pyproject.toml"
        assert os.path.exists(pyproject_path)

        with open(pyproject_path, "r") as f:
            content = f.read()

        # Check for required metadata
        required_fields = [
            'name = "praier"',
            "version =",
            "description =",
            "dependencies =",
        ]

        for field in required_fields:
            assert field in content, f"Missing metadata field: {field}"

    def test_development_dependencies(self):
        """Test that development dependencies are properly defined."""
        pyproject_path = "/home/runner/work/praier/praier/pyproject.toml"

        with open(pyproject_path, "r") as f:
            content = f.read()

        # Check for dev dependencies
        dev_deps = ["pytest", "black", "isort", "flake8", "mypy"]
        for dep in dev_deps:
            assert dep in content, f"Missing development dependency: {dep}"


class TestConfigurationExamples:
    """Test class for configuration example validation."""

    def test_config_example_exists(self):
        """Test that config example file exists."""
        config_path = "/home/runner/work/praier/praier/config.example.yaml"
        assert os.path.exists(config_path)

    def test_config_example_valid_yaml(self):
        """Test that config example is valid YAML."""
        config_path = "/home/runner/work/praier/praier/config.example.yaml"

        import yaml

        with open(config_path, "r") as f:
            try:
                yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Config example is not valid YAML: {e}")

    def test_env_example_exists(self):
        """Test that environment example file exists."""
        env_path = "/home/runner/work/praier/praier/.env.example"
        assert os.path.exists(env_path)

    def test_env_example_content(self):
        """Test that environment example has required variables."""
        env_path = "/home/runner/work/praier/praier/.env.example"

        with open(env_path, "r") as f:
            content = f.read()

        # Check for required environment variables
        required_vars = [
            "GITHUB_TOKEN",
            "PRAIER_REPOSITORIES",
            "PRAIER_POLL_INTERVAL",
        ]

        for var in required_vars:
            assert var in content, f"Missing environment variable example: {var}"


if __name__ == "__main__":
    pytest.main([__file__])
