"""
Configuration management for Praier.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class GitHubConfig:
    """Configuration for a GitHub server instance."""

    url: str = "https://api.github.com"
    token: str = ""
    name: str = "default"

    @classmethod
    def from_env(cls, prefix: str = "") -> "GitHubConfig":
        """Create configuration from environment variables."""
        if prefix:
            prefix = f"{prefix}_"

        return cls(
            url=os.getenv(f"{prefix}GITHUB_URL", "https://api.github.com"),
            token=os.getenv(f"{prefix}GITHUB_TOKEN", ""),
            name=os.getenv(f"{prefix}GITHUB_NAME", "default"),
        )


@dataclass
class AgentConfig:
    """Configuration for agent team behavior."""

    enabled: bool = True
    developer_enabled: bool = True
    tester_enabled: bool = True
    documentation_enabled: bool = True
    project_manager_enabled: bool = True


@dataclass
class MonitoringConfig:
    """Configuration for PR monitoring behavior."""

    poll_interval: int = 60  # seconds
    max_concurrent_requests: int = 10
    repositories: List[str] = None  # e.g., ["owner/repo1", "owner/repo2"]
    auto_approve_actions: bool = True
    auto_fix_with_copilot: bool = True

    def __post_init__(self):
        if self.repositories is None:
            self.repositories = []


@dataclass
class PraierConfig:
    """Main configuration for Praier."""

    github_servers: List[GitHubConfig] = None
    monitoring: MonitoringConfig = None
    agents: AgentConfig = None
    log_level: str = "INFO"

    def __post_init__(self):
        if self.github_servers is None:
            self.github_servers = [GitHubConfig.from_env()]
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.agents is None:
            self.agents = AgentConfig()

    @classmethod
    def load_from_file(cls, config_path: str) -> "PraierConfig":
        """Load configuration from YAML file."""
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        github_servers = []
        for server_data in data.get("github_servers", []):
            github_servers.append(GitHubConfig(**server_data))

        monitoring_data = data.get("monitoring", {})
        monitoring = MonitoringConfig(**monitoring_data)

        agents_data = data.get("agents", {})
        agents = AgentConfig(**agents_data)

        return cls(
            github_servers=github_servers,
            monitoring=monitoring,
            agents=agents,
            log_level=data.get("log_level", "INFO"),
        )

    @classmethod
    def load_from_env(cls) -> "PraierConfig":
        """Load configuration from environment variables."""
        load_dotenv()

        # Load main GitHub server
        main_server = GitHubConfig.from_env()
        github_servers = [main_server]

        # Load additional servers if configured
        server_count = int(os.getenv("PRAIER_SERVER_COUNT", "1"))
        for i in range(1, server_count):
            server = GitHubConfig.from_env(f"GITHUB_{i}")
            github_servers.append(server)

        # Load monitoring config
        monitoring = MonitoringConfig(
            poll_interval=int(os.getenv("PRAIER_POLL_INTERVAL", "60")),
            max_concurrent_requests=int(os.getenv("PRAIER_MAX_CONCURRENT", "10")),
            repositories=(
                os.getenv("PRAIER_REPOSITORIES", "").split(",")
                if os.getenv("PRAIER_REPOSITORIES")
                else []
            ),
            auto_approve_actions=os.getenv("PRAIER_AUTO_APPROVE", "true").lower()
            == "true",
            auto_fix_with_copilot=os.getenv("PRAIER_AUTO_FIX", "true").lower()
            == "true",
        )

        # Load agent config
        agents = AgentConfig(
            enabled=os.getenv("PRAIER_AGENTS_ENABLED", "true").lower() == "true",
            developer_enabled=os.getenv("PRAIER_AGENT_DEVELOPER", "true").lower()
            == "true",
            tester_enabled=os.getenv("PRAIER_AGENT_TESTER", "true").lower() == "true",
            documentation_enabled=os.getenv(
                "PRAIER_AGENT_DOCUMENTATION", "true"
            ).lower()
            == "true",
            project_manager_enabled=os.getenv(
                "PRAIER_AGENT_PROJECT_MANAGER", "true"
            ).lower()
            == "true",
        )

        return cls(
            github_servers=github_servers,
            monitoring=monitoring,
            agents=agents,
            log_level=os.getenv("PRAIER_LOG_LEVEL", "INFO"),
        )
