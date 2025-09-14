"""
Tests for the Praier CLI module.
"""

import os
import tempfile
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from praier.cli import cli, setup_logging
from praier.config import PraierConfig, GitHubConfig, MonitoringConfig


class TestCLI:
    """Test class for CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_setup_logging_info_level(self):
        """Test logging setup with INFO level."""
        setup_logging("INFO")
        # Test that logging was configured (no exceptions)
        assert True

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        setup_logging("DEBUG")
        # Test that logging was configured (no exceptions)
        assert True

    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Praier' in result.output
        assert 'monitor' in result.output
        assert 'status' in result.output

    def test_status_command_no_token(self):
        """Test status command with no GitHub token."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.runner.invoke(cli, ['status'])
            assert result.exit_code == 0
            assert 'GitHub Servers: 1' in result.output
            assert 'Token: ✗' in result.output

    def test_status_command_with_token(self):
        """Test status command with GitHub token."""
        env = {
            'GITHUB_TOKEN': 'test-token',
            'PRAIER_REPOSITORIES': 'owner/repo1,owner/repo2'
        }
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['status'])
            assert result.exit_code == 0
            assert 'GitHub Servers: 1' in result.output
            assert 'Token: ✓' in result.output
            assert 'owner/repo1' in result.output
            assert 'owner/repo2' in result.output

    def test_generate_config_stdout(self):
        """Test generate-config command output to stdout."""
        result = self.runner.invoke(cli, ['generate-config'])
        assert result.exit_code == 0
        assert 'github_servers:' in result.output
        assert 'monitoring:' in result.output
        assert 'poll_interval' in result.output

    def test_generate_config_file(self):
        """Test generate-config command output to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            result = self.runner.invoke(cli, ['generate-config', '--output', f.name])
            assert result.exit_code == 0
            assert f'Sample configuration written to {f.name}' in result.output
            
            # Check file contents
            with open(f.name, 'r') as content_file:
                content = content_file.read()
                assert 'github_servers:' in content
                assert 'monitoring:' in content
            
            # Clean up
            os.unlink(f.name)

    def test_monitor_command_no_token(self):
        """Test monitor command with no GitHub token."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.runner.invoke(cli, ['monitor'])
            assert result.exit_code == 1
            assert 'No GitHub tokens configured' in result.output

    def test_monitor_command_no_repositories(self):
        """Test monitor command with no repositories configured."""
        env = {'GITHUB_TOKEN': 'test-token'}
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['monitor'])
            assert result.exit_code == 1
            assert 'No repositories configured' in result.output

    @patch('praier.cli.PRMonitor')
    @patch('asyncio.run')
    def test_monitor_command_success(self, mock_asyncio_run, mock_pr_monitor):
        """Test successful monitor command execution."""
        env = {
            'GITHUB_TOKEN': 'test-token',
            'PRAIER_REPOSITORIES': 'owner/repo1'
        }
        
        # Mock the monitor instance
        mock_monitor_instance = MagicMock()
        mock_pr_monitor.return_value = mock_monitor_instance
        
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['monitor'])
            assert result.exit_code == 0
            assert 'Starting Praier PR monitor' in result.output
            assert 'owner/repo1' in result.output
            
            # Verify monitor was created and started
            mock_pr_monitor.assert_called_once()
            mock_asyncio_run.assert_called_once()

    @patch('praier.cli.PRMonitor')
    @patch('asyncio.run')
    def test_monitor_command_keyboard_interrupt(self, mock_asyncio_run, mock_pr_monitor):
        """Test monitor command with keyboard interrupt."""
        env = {
            'GITHUB_TOKEN': 'test-token',
            'PRAIER_REPOSITORIES': 'owner/repo1'
        }
        
        # Mock keyboard interrupt
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['monitor'])
            assert result.exit_code == 0
            assert 'Shutting down gracefully' in result.output

    @patch('praier.github_client.GitHubClient')
    def test_test_connection_success(self, mock_github_client):
        """Test successful connection test."""
        env = {'GITHUB_TOKEN': 'test-token'}
        
        # Mock GitHub client and PRs
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        from praier.github_client import PullRequest
        from datetime import datetime
        
        mock_prs = [
            PullRequest(
                id="1", number=1, title="Test PR 1", url="url1", state="open",
                head_sha="sha1", base_ref="main", head_ref="feature1", author="user1",
                repository="owner/repo", created_at=datetime.now(), updated_at=datetime.now(),
                draft=False
            ),
            PullRequest(
                id="2", number=2, title="Test PR 2", url="url2", state="open",
                head_sha="sha2", base_ref="main", head_ref="feature2", author="user2",
                repository="owner/repo", created_at=datetime.now(), updated_at=datetime.now(),
                draft=False
            )
        ]
        mock_client_instance.get_pull_requests.return_value = mock_prs
        
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['test-connection', 'owner/repo'])
            assert result.exit_code == 0
            assert 'Successfully connected' in result.output
            assert 'Found 2 open pull requests' in result.output
            assert 'Test PR 1' in result.output

    def test_test_connection_no_token(self):
        """Test connection test with no token."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.runner.invoke(cli, ['test-connection', 'owner/repo'])
            assert result.exit_code == 1
            assert 'No token configured' in result.output

    def test_test_connection_invalid_server(self):
        """Test connection test with invalid server name."""
        env = {'GITHUB_TOKEN': 'test-token'}
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['test-connection', 'owner/repo', '--server', 'nonexistent'])
            assert result.exit_code == 1
            assert "Server 'nonexistent' not found" in result.output

    @patch('praier.github_client.GitHubClient')
    def test_test_connection_failure(self, mock_github_client):
        """Test connection test failure."""
        env = {'GITHUB_TOKEN': 'test-token'}
        
        # Mock connection failure
        mock_github_client.side_effect = Exception("Connection failed")
        
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['test-connection', 'owner/repo'])
            assert result.exit_code == 1
            assert 'Connection failed' in result.output

    def test_config_file_loading(self):
        """Test loading configuration from file."""
        config_content = """
github_servers:
  - name: "test"
    url: "https://api.github.com"
    token: "test-token"

monitoring:
  poll_interval: 30
  repositories:
    - "owner/repo1"
  auto_approve_actions: true

log_level: "DEBUG"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            result = self.runner.invoke(cli, ['--config', f.name, 'status'])
            assert result.exit_code == 0
            assert 'GitHub Servers: 1' in result.output
            assert 'owner/repo1' in result.output
            
            # Clean up
            os.unlink(f.name)

    def test_log_level_override(self):
        """Test log level override via command line."""
        env = {'GITHUB_TOKEN': 'test-token'}
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(cli, ['--log-level', 'DEBUG', 'status'])
            assert result.exit_code == 0
            # Test passes if no errors occur


if __name__ == '__main__':
    pytest.main([__file__])