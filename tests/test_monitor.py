"""
Tests for the Praier monitor module.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from praier.monitor import PRMonitor, PRState
from praier.config import PraierConfig, GitHubConfig, MonitoringConfig
from praier.github_client import PullRequest, CheckRun, WorkflowRun


class TestPRState:
    """Test class for PRState functionality."""

    def test_pr_state_creation(self):
        """Test PRState dataclass creation."""
        pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        state = PRState(pr=pr)
        
        assert state.pr == pr
        assert state.last_check_runs == {}
        assert state.last_workflow_runs == {}
        assert state.copilot_requested == False
        assert state.approved_runs == set()
        assert isinstance(state.last_updated, datetime)


class TestPRMonitor:
    """Test class for PRMonitor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = PraierConfig(
            github_servers=[
                GitHubConfig(name="test", url="https://api.github.com", token="test-token")
            ],
            monitoring=MonitoringConfig(
                poll_interval=60,
                repositories=["owner/repo1", "owner/repo2"],
                auto_approve_actions=True,
                auto_fix_with_copilot=True
            ),
            log_level="INFO"
        )

    @patch('praier.monitor.GitHubClient')
    def test_monitor_initialization(self, mock_github_client):
        """Test PRMonitor initialization."""
        monitor = PRMonitor(self.config)
        
        assert len(monitor.clients) == 1
        assert "test" in monitor.clients
        assert "test" in monitor.pr_states
        assert monitor.config == self.config
        
        # Verify GitHub client was created
        mock_github_client.assert_called_once_with("https://api.github.com", "test-token")

    @patch('praier.monitor.GitHubClient')
    def test_monitor_initialization_no_token(self, mock_github_client):
        """Test PRMonitor initialization with no token."""
        config = PraierConfig(
            github_servers=[
                GitHubConfig(name="test", url="https://api.github.com", token="")
            ],
            monitoring=MonitoringConfig(repositories=["owner/repo1"]),
            log_level="INFO"
        )
        
        monitor = PRMonitor(config)
        
        # Should skip servers without tokens
        assert len(monitor.clients) == 0
        mock_github_client.assert_not_called()

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_start_monitoring_no_clients(self, mock_github_client):
        """Test start_monitoring with no valid clients."""
        config = PraierConfig(
            github_servers=[
                GitHubConfig(name="test", url="https://api.github.com", token="")
            ],
            monitoring=MonitoringConfig(repositories=["owner/repo1"]),
            log_level="INFO"
        )
        
        monitor = PRMonitor(config)
        
        # Should exit immediately with no clients
        await monitor.start_monitoring()
        assert len(monitor.clients) == 0

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_monitor_cycle(self, mock_github_client):
        """Test a single monitoring cycle."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        monitor = PRMonitor(self.config)
        
        # Mock the monitor_server method
        monitor.monitor_server = AsyncMock()
        
        await monitor.monitor_cycle()
        
        # Verify monitor_server was called for each client
        monitor.monitor_server.assert_called_once()

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_monitor_server_no_repositories(self, mock_github_client):
        """Test monitoring server with no repositories configured."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        config = PraierConfig(
            github_servers=[GitHubConfig(name="test", url="https://api.github.com", token="test-token")],
            monitoring=MonitoringConfig(repositories=[]),
            log_level="INFO"
        )
        
        monitor = PRMonitor(config)
        server_info = monitor.clients["test"]
        
        # Should not crash with no repositories
        await monitor.monitor_server("test", server_info)

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_monitor_repository(self, mock_github_client):
        """Test monitoring a single repository."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        # Mock pull requests
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        mock_client_instance.get_pull_requests.return_value = [mock_pr]
        
        monitor = PRMonitor(self.config)
        
        # Mock process_pull_request method
        monitor.process_pull_request = AsyncMock()
        
        await monitor.monitor_repository("test", mock_client_instance, "owner/repo1")
        
        # Verify get_pull_requests was called
        mock_client_instance.get_pull_requests.assert_called_once_with("owner/repo1", state="open")
        
        # Verify process_pull_request was called for each PR
        monitor.process_pull_request.assert_called_once_with("test", mock_client_instance, "owner/repo1", mock_pr)

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_process_pull_request_new_pr(self, mock_github_client):
        """Test processing a new pull request."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        # Mock API responses
        mock_client_instance.get_workflow_runs.return_value = []
        mock_client_instance.get_check_runs.return_value = []
        
        monitor = PRMonitor(self.config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        await monitor.process_pull_request("test", mock_client_instance, "owner/repo1", mock_pr)
        
        # Verify PR state was created
        assert 123 in monitor.pr_states["test"]
        pr_state = monitor.pr_states["test"][123]
        assert pr_state.pr == mock_pr

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_process_workflow_runs_auto_approve(self, mock_github_client):
        """Test processing workflow runs with auto-approval."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        mock_client_instance.approve_workflow_run.return_value = True
        
        monitor = PRMonitor(self.config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        mock_workflow_run = WorkflowRun(
            id="run-123", name="CI Tests", status="queued", conclusion=None,
            url="test-url", head_sha="abc123", pull_requests=[123]
        )
        
        pr_state = PRState(pr=mock_pr)
        
        await monitor.process_workflow_runs(
            "test", mock_client_instance, "owner/repo1", mock_pr, [mock_workflow_run], pr_state
        )
        
        # Verify approval was attempted
        mock_client_instance.approve_workflow_run.assert_called_once_with("owner/repo1", "run-123")
        
        # Verify run was marked as approved
        assert "run-123" in pr_state.approved_runs

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_process_workflow_runs_no_auto_approve(self, mock_github_client):
        """Test processing workflow runs with auto-approval disabled."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        config = PraierConfig(
            github_servers=[GitHubConfig(name="test", url="https://api.github.com", token="test-token")],
            monitoring=MonitoringConfig(auto_approve_actions=False),
            log_level="INFO"
        )
        
        monitor = PRMonitor(config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        mock_workflow_run = WorkflowRun(
            id="run-123", name="CI Tests", status="queued", conclusion=None,
            url="test-url", head_sha="abc123", pull_requests=[123]
        )
        
        pr_state = PRState(pr=mock_pr)
        
        await monitor.process_workflow_runs(
            "test", mock_client_instance, "owner/repo1", mock_pr, [mock_workflow_run], pr_state
        )
        
        # Verify no approval was attempted
        mock_client_instance.approve_workflow_run.assert_not_called()

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_process_check_runs_copilot_request(self, mock_github_client):
        """Test processing check runs with Copilot fix request."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        mock_client_instance.request_copilot_fix.return_value = True
        
        monitor = PRMonitor(self.config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        mock_check_run = CheckRun(
            id="check-123", name="Unit Tests", status="completed", conclusion="failure",
            url="test-url"
        )
        
        pr_state = PRState(pr=mock_pr)
        
        await monitor.process_check_runs(
            "test", mock_client_instance, "owner/repo1", mock_pr, [mock_check_run], pr_state
        )
        
        # Verify Copilot fix was requested
        mock_client_instance.request_copilot_fix.assert_called_once_with("owner/repo1", 123, [mock_check_run])
        
        # Verify flag was set
        assert pr_state.copilot_requested == True

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_process_check_runs_no_auto_fix(self, mock_github_client):
        """Test processing check runs with auto-fix disabled."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        config = PraierConfig(
            github_servers=[GitHubConfig(name="test", url="https://api.github.com", token="test-token")],
            monitoring=MonitoringConfig(auto_fix_with_copilot=False),
            log_level="INFO"
        )
        
        monitor = PRMonitor(config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        mock_check_run = CheckRun(
            id="check-123", name="Unit Tests", status="completed", conclusion="failure",
            url="test-url"
        )
        
        pr_state = PRState(pr=mock_pr)
        
        await monitor.process_check_runs(
            "test", mock_client_instance, "owner/repo1", mock_pr, [mock_check_run], pr_state
        )
        
        # Verify no Copilot fix was requested
        mock_client_instance.request_copilot_fix.assert_not_called()

    @patch('praier.monitor.GitHubClient')
    def test_get_monitoring_stats(self, mock_github_client):
        """Test getting monitoring statistics."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        monitor = PRMonitor(self.config)
        
        # Add some PR states
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        monitor.pr_states["test"][123] = PRState(pr=mock_pr)
        monitor.pr_states["test"][124] = PRState(pr=mock_pr)
        
        stats = monitor.get_monitoring_stats()
        
        assert stats['servers'] == 1
        assert stats['total_prs'] == 2
        assert stats['active_prs_by_server']['test'] == 2
        assert stats['repositories'] == ["owner/repo1", "owner/repo2"]

    @patch('praier.monitor.GitHubClient')
    def test_cleanup_stale_prs(self, mock_github_client):
        """Test cleaning up stale PR states."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        monitor = PRMonitor(self.config)
        
        # Add fresh and stale PR states
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        fresh_state = PRState(pr=mock_pr)
        fresh_state.last_updated = datetime.now()
        
        stale_state = PRState(pr=mock_pr)
        stale_state.last_updated = datetime.now() - timedelta(hours=25)
        
        monitor.pr_states["test"][123] = fresh_state
        monitor.pr_states["test"][124] = stale_state
        
        monitor.cleanup_stale_prs(max_age_hours=24)
        
        # Verify stale PR was removed but fresh one remains
        assert 123 in monitor.pr_states["test"]
        assert 124 not in monitor.pr_states["test"]

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_workflow_run_already_approved(self, mock_github_client):
        """Test that already approved workflow runs are skipped."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        monitor = PRMonitor(self.config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="abc123", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        mock_workflow_run = WorkflowRun(
            id="run-123", name="CI Tests", status="queued", conclusion=None,
            url="test-url", head_sha="abc123", pull_requests=[123]
        )
        
        pr_state = PRState(pr=mock_pr)
        pr_state.approved_runs.add("run-123")  # Mark as already approved
        
        await monitor.process_workflow_runs(
            "test", mock_client_instance, "owner/repo1", mock_pr, [mock_workflow_run], pr_state
        )
        
        # Verify no approval was attempted
        mock_client_instance.approve_workflow_run.assert_not_called()

    @patch('praier.monitor.GitHubClient')
    @pytest.mark.asyncio
    async def test_copilot_request_reset_on_sha_change(self, mock_github_client):
        """Test that Copilot request flag is reset when SHA changes."""
        mock_client_instance = MagicMock()
        mock_github_client.return_value = mock_client_instance
        
        monitor = PRMonitor(self.config)
        
        mock_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="new-sha", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        # Create PR state with old SHA and copilot requested
        old_pr = PullRequest(
            id="1", number=123, title="Test PR", url="test-url", state="open",
            head_sha="old-sha", base_ref="main", head_ref="feature", author="user",
            repository="owner/repo1", created_at=datetime.now(), updated_at=datetime.now(),
            draft=False
        )
        
        pr_state = PRState(pr=old_pr)
        pr_state.copilot_requested = True
        
        await monitor.process_check_runs(
            "test", mock_client_instance, "owner/repo1", mock_pr, [], pr_state
        )
        
        # Verify flag was reset due to SHA change
        assert pr_state.copilot_requested == False


if __name__ == '__main__':
    pytest.main([__file__])