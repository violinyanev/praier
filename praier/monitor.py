"""
Core monitoring logic for pull requests and workflow runs.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple

from .agents import AgentTeam, create_default_team
from .config import GitHubConfig, PraierConfig
from .github_client import CheckRun, GitHubClient, PullRequest, WorkflowRun

logger = logging.getLogger(__name__)


@dataclass
class PRState:
    """Tracks the state of a pull request for change detection."""

    pr: PullRequest
    last_check_runs: Dict[str, CheckRun] = field(default_factory=dict)
    last_workflow_runs: Dict[str, WorkflowRun] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    copilot_requested: bool = False
    approved_runs: Set[str] = field(default_factory=set)


class PRMonitor:
    """Monitors pull requests and handles automatic actions."""

    def __init__(self, config: PraierConfig):
        self.config = config
        self.clients = {}
        self.pr_states: Dict[str, Dict[int, PRState]] = (
            {}
        )  # server_name -> pr_number -> state

        # Initialize agent team
        self.agent_team = None
        if config.agents.enabled:
            self.agent_team = create_default_team()

            # Configure individual agents based on config
            if not config.agents.developer_enabled:
                agent = self.agent_team.get_agent("Developer")
                if agent:
                    agent.disable()

            if not config.agents.tester_enabled:
                agent = self.agent_team.get_agent("Tester")
                if agent:
                    agent.disable()

            if not config.agents.documentation_enabled:
                agent = self.agent_team.get_agent("Documentation")
                if agent:
                    agent.disable()

            if not config.agents.project_manager_enabled:
                agent = self.agent_team.get_agent("ProjectManager")
                if agent:
                    agent.disable()

            logger.info(
                f"Agent team initialized with {len(self.agent_team.list_agents())} agents"
            )

        # Initialize GitHub clients
        for github_config in config.github_servers:
            if not github_config.token:
                logger.warning(
                    f"No token provided for GitHub server '{github_config.name}', skipping"
                )
                continue

            client = GitHubClient(github_config.url, github_config.token)
            self.clients[github_config.name] = {
                "client": client,
                "config": github_config,
            }
            self.pr_states[github_config.name] = {}

    async def start_monitoring(self):
        """Start the main monitoring loop."""
        logger.info("Starting PR monitoring...")

        if not self.clients:
            logger.error("No valid GitHub clients configured. Exiting.")
            return

        while True:
            try:
                await self.monitor_cycle()
                await asyncio.sleep(self.config.monitoring.poll_interval)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
                await asyncio.sleep(min(self.config.monitoring.poll_interval, 30))

    async def monitor_cycle(self):
        """Perform one monitoring cycle across all configured servers."""
        logger.debug("Starting monitoring cycle")

        tasks = []
        for server_name, server_info in self.clients.items():
            task = asyncio.create_task(self.monitor_server(server_name, server_info))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug("Monitoring cycle completed")

    async def monitor_server(self, server_name: str, server_info: Dict):
        """Monitor all repositories on a single GitHub server."""
        client = server_info["client"]
        github_config = server_info["config"]

        repositories = self.config.monitoring.repositories
        if not repositories:
            logger.warning(
                f"No repositories configured for monitoring on {server_name}"
            )
            return

        for repository in repositories:
            try:
                await self.monitor_repository(server_name, client, repository)
            except Exception as e:
                logger.error(
                    f"Error monitoring repository {repository} on {server_name}: {e}"
                )

    async def monitor_repository(
        self, server_name: str, client: GitHubClient, repository: str
    ):
        """Monitor a single repository for PR changes."""
        logger.debug(f"Monitoring repository {repository} on {server_name}")

        try:
            # Get current pull requests
            pull_requests = client.get_pull_requests(repository, state="open")

            for pr in pull_requests:
                await self.process_pull_request(server_name, client, repository, pr)

        except Exception as e:
            logger.error(f"Failed to fetch PRs for {repository}: {e}")

    async def process_pull_request(
        self, server_name: str, client: GitHubClient, repository: str, pr: PullRequest
    ):
        """Process a single pull request and detect changes."""
        pr_key = f"{repository}#{pr.number}"

        # Get or create PR state
        if pr.number not in self.pr_states[server_name]:
            self.pr_states[server_name][pr.number] = PRState(pr=pr)
            logger.info(f"Started monitoring {pr_key} - {pr.title}")

        pr_state = self.pr_states[server_name][pr.number]

        # Update PR info
        pr_state.pr = pr
        pr_state.last_updated = datetime.now()

        # Get current workflow runs and check runs
        try:
            workflow_runs = client.get_workflow_runs(repository, head_sha=pr.head_sha)
            check_runs = client.get_check_runs(repository, pr.head_sha)

            # Run agent analysis if enabled
            if self.agent_team:
                try:
                    reports = await self.agent_team.analyze_pr(
                        pr, repository, check_runs, workflow_runs
                    )

                    if reports:
                        summary = self.agent_team.get_team_summary(reports)
                        logger.info(
                            f"Agent team analysis for {pr_key}: "
                            f"{summary['total_findings']} findings, "
                            f"priority: {summary['overall_priority']}"
                        )

                        # Log individual agent summaries
                        for agent_name, agent_summary in summary[
                            "agent_summaries"
                        ].items():
                            logger.debug(f"  {agent_name}: {agent_summary}")

                except Exception as e:
                    logger.error(f"Agent team analysis failed for {pr_key}: {e}")

            # Process workflow runs
            await self.process_workflow_runs(
                server_name, client, repository, pr, workflow_runs, pr_state
            )

            # Process check runs
            await self.process_check_runs(
                server_name, client, repository, pr, check_runs, pr_state
            )

        except Exception as e:
            logger.error(f"Error processing {pr_key}: {e}")

    async def process_workflow_runs(
        self,
        server_name: str,
        client: GitHubClient,
        repository: str,
        pr: PullRequest,
        workflow_runs: List[WorkflowRun],
        pr_state: PRState,
    ):
        """Process workflow runs for auto-approval."""
        if not self.config.monitoring.auto_approve_actions:
            return

        pr_key = f"{repository}#{pr.number}"

        for run in workflow_runs:
            # Skip if this run doesn't belong to this PR
            if pr.number not in run.pull_requests:
                continue

            # Skip if already approved
            if run.id in pr_state.approved_runs:
                continue

            # Check if run needs approval (status is "queued" often indicates pending approval)
            if run.status in ["queued", "waiting"]:
                logger.info(f"Attempting to approve workflow run {run.id} for {pr_key}")

                if client.approve_workflow_run(repository, run.id):
                    pr_state.approved_runs.add(run.id)
                    logger.info(f"Auto-approved workflow run '{run.name}' for {pr_key}")

        # Update tracked workflow runs
        pr_state.last_workflow_runs = {run.id: run for run in workflow_runs}

    async def process_check_runs(
        self,
        server_name: str,
        client: GitHubClient,
        repository: str,
        pr: PullRequest,
        check_runs: List[CheckRun],
        pr_state: PRState,
    ):
        """Process check runs and request Copilot fixes if needed."""
        if not self.config.monitoring.auto_fix_with_copilot:
            return

        pr_key = f"{repository}#{pr.number}"

        # Find failing checks
        failing_checks = [
            check
            for check in check_runs
            if check.status == "completed" and check.conclusion == "failure"
        ]

        if failing_checks and not pr_state.copilot_requested:
            # Only request fix once per PR head SHA
            logger.info(f"Found {len(failing_checks)} failing checks for {pr_key}")

            if client.request_copilot_fix(repository, pr.number, failing_checks):
                pr_state.copilot_requested = True
                logger.info(f"Requested Copilot fix for {pr_key}")

        # Reset copilot_requested flag if head SHA changed (new commits pushed)
        if pr_state.pr.head_sha != pr.head_sha:
            pr_state.copilot_requested = False

        # Update tracked check runs
        pr_state.last_check_runs = {check.id: check for check in check_runs}

    def get_monitoring_stats(self) -> Dict:
        """Get statistics about current monitoring state."""
        stats = {
            "servers": len(self.clients),
            "total_prs": 0,
            "active_prs_by_server": {},
            "repositories": (
                self.config.monitoring.repositories.copy()
                if self.config.monitoring.repositories
                else []
            ),
        }

        for server_name, pr_states in self.pr_states.items():
            active_prs = len(pr_states)
            stats["total_prs"] += active_prs
            stats["active_prs_by_server"][server_name] = active_prs

        return stats

    def cleanup_stale_prs(self, max_age_hours: int = 24):
        """Remove PR states for PRs that haven't been updated recently."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        for server_name, pr_states in self.pr_states.items():
            stale_prs = [
                pr_num
                for pr_num, state in pr_states.items()
                if state.last_updated < cutoff_time
            ]

            for pr_num in stale_prs:
                del pr_states[pr_num]
                logger.debug(
                    f"Cleaned up stale PR state for #{pr_num} on {server_name}"
                )
