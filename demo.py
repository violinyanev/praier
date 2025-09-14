#!/usr/bin/env python3
"""
Demo script showing how Praier monitors and acts on PRs.
This is a simulation for demonstration purposes.
"""

import asyncio
import logging
from datetime import datetime

from praier.config import GitHubConfig, MonitoringConfig, PraierConfig
from praier.github_client import CheckRun, PullRequest, WorkflowRun
from praier.monitor import PRMonitor

# Configure logging for demo
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockGitHubClient:
    """Mock GitHub client for demonstration."""

    def __init__(self, *args, **kwargs):
        self.approved_runs = set()
        self.copilot_requests = set()

    def get_pull_requests(self, repository, state="open"):
        """Return mock PRs."""
        return [
            PullRequest(
                id="MDExOlB1bGxSZXF1ZXN0Nzk5NTI4NTEx",
                number=123,
                title="Add new feature",
                url="https://github.com/owner/repo/pull/123",
                state="open",
                head_sha="abc123def456",
                base_ref="main",
                head_ref="feature-branch",
                author="developer",
                repository=repository,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                draft=False,
            )
        ]

    def get_workflow_runs(self, repository, head_sha=None):
        """Return mock workflow runs."""
        return [
            WorkflowRun(
                id="12345",
                name="CI Tests",
                status="queued",  # This will trigger auto-approval
                conclusion=None,
                url="https://github.com/owner/repo/actions/runs/12345",
                head_sha=head_sha or "abc123def456",
                pull_requests=[123],
            )
        ]

    def get_check_runs(self, repository, ref):
        """Return mock check runs."""
        return [
            CheckRun(
                id="67890",
                name="Unit Tests",
                status="completed",
                conclusion="failure",  # This will trigger Copilot request
                url="https://github.com/owner/repo/runs/67890",
            ),
            CheckRun(
                id="67891",
                name="Lint Check",
                status="completed",
                conclusion="failure",
                url="https://github.com/owner/repo/runs/67891",
            ),
        ]

    def approve_workflow_run(self, repository, run_id):
        """Mock workflow approval."""
        logger.info(f"🚀 Auto-approved workflow run {run_id} in {repository}")
        self.approved_runs.add(run_id)
        return True

    def request_copilot_fix(self, repository, pr_number, failing_checks):
        """Mock Copilot fix request."""
        check_names = [check.name for check in failing_checks]
        logger.info(
            f"🤖 Requested GitHub Copilot fix for PR #{pr_number} in {repository}"
        )
        logger.info(f"   Failing checks: {', '.join(check_names)}")
        self.copilot_requests.add(pr_number)
        return True


async def demo_monitoring():
    """Demonstrate PR monitoring functionality."""
    print("🎯 Praier Demo - GitHub PR Monitoring Tool")
    print("=" * 50)

    # Create demo configuration
    config = PraierConfig(
        github_servers=[
            GitHubConfig(
                name="demo",
                url="https://api.github.com",
                token="demo-token-would-be-here",
            )
        ],
        monitoring=MonitoringConfig(
            poll_interval=5,  # Short interval for demo
            repositories=["owner/demo-repo"],
            auto_approve_actions=True,
            auto_fix_with_copilot=True,
        ),
        log_level="INFO",
    )

    # Create monitor with mock client
    monitor = PRMonitor(config)

    # Replace the real GitHub client with our mock
    mock_client = MockGitHubClient()
    monitor.clients["demo"] = {
        "client": mock_client,
        "config": config.github_servers[0],
    }

    print("📊 Configuration:")
    print(f"   Servers: {len(config.github_servers)}")
    print(f"   Repositories: {config.monitoring.repositories}")
    print(f"   Poll interval: {config.monitoring.poll_interval}s")
    print(f"   Auto-approve: {config.monitoring.auto_approve_actions}")
    print(f"   Auto-fix: {config.monitoring.auto_fix_with_copilot}")
    print()

    print("🔍 Starting monitoring simulation...")
    print("   This demo will run 3 monitoring cycles to show functionality")
    print()

    # Run a few monitoring cycles
    for cycle in range(1, 4):
        print(f"📅 Monitoring Cycle #{cycle}")
        print("-" * 30)

        try:
            await monitor.monitor_cycle()

            # Show what happened
            if mock_client.approved_runs:
                print(f"   ✅ Approved {len(mock_client.approved_runs)} workflow runs")

            if mock_client.copilot_requests:
                print(
                    f"   🤖 Requested Copilot fixes for "
                    f"{len(mock_client.copilot_requests)} PRs"
                )

            # Get stats
            stats = monitor.get_monitoring_stats()
            print(
                f"   📈 Stats: {stats['total_prs']} PRs tracked across "
                f"{stats['servers']} servers"
            )

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        if cycle < 3:
            print(f"⏱️  Waiting {config.monitoring.poll_interval}s until next cycle...")
            await asyncio.sleep(config.monitoring.poll_interval)

    print("✨ Demo completed!")
    print("\nIn a real deployment, Praier would:")
    print("• Connect to actual GitHub servers using your tokens")
    print("• Monitor real repositories for PR changes")
    print("• Automatically approve workflow runs needing approval")
    print("• Request GitHub Copilot fixes for failing checks")
    print("• Run continuously in the background")
    print("\nTo get started:")
    print("1. Set GITHUB_TOKEN environment variable")
    print("2. Set PRAIER_REPOSITORIES to your repos")
    print("3. Run: praier monitor")


if __name__ == "__main__":
    asyncio.run(demo_monitoring())
