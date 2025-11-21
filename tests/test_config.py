"""
Tests for the Praier configuration module.
"""

import os
import tempfile

from praier.config import GitHubConfig, MonitoringConfig, PraierConfig


def test_github_config_from_env():
    """Test GitHubConfig creation from environment variables."""
    # Set environment variables
    os.environ["GITHUB_TOKEN"] = "test-token"
    os.environ["GITHUB_URL"] = "https://github.example.com/api/v3"
    os.environ["GITHUB_NAME"] = "test-server"

    config = GitHubConfig.from_env()

    assert config.token == "test-token"
    assert config.url == "https://github.example.com/api/v3"
    assert config.name == "test-server"

    # Clean up
    del os.environ["GITHUB_TOKEN"]
    del os.environ["GITHUB_URL"]
    del os.environ["GITHUB_NAME"]


def test_github_config_defaults():
    """Test GitHubConfig defaults when no env vars are set."""
    config = GitHubConfig.from_env()

    assert config.url == "https://api.github.com"
    assert config.token == ""
    assert config.name == "default"


def test_praier_config_from_env():
    """Test PraierConfig creation from environment variables."""
    os.environ["GITHUB_TOKEN"] = "test-token"
    os.environ["PRAIER_REPOSITORIES"] = "owner/repo1,owner/repo2"
    os.environ["PRAIER_POLL_INTERVAL"] = "30"
    os.environ["PRAIER_AUTO_APPROVE"] = "false"

    config = PraierConfig.load_from_env()

    assert len(config.github_servers) == 1
    assert config.github_servers[0].token == "test-token"
    assert config.monitoring.repositories == ["owner/repo1", "owner/repo2"]
    assert config.monitoring.poll_interval == 30
    assert config.monitoring.auto_approve_actions == False

    # Clean up
    del os.environ["GITHUB_TOKEN"]
    del os.environ["PRAIER_REPOSITORIES"]
    del os.environ["PRAIER_POLL_INTERVAL"]
    del os.environ["PRAIER_AUTO_APPROVE"]


def test_praier_config_from_yaml():
    """Test PraierConfig creation from YAML file."""
    yaml_content = """
github_servers:
  - name: "test"
    url: "https://api.github.com"
    token: "test-token"

monitoring:
  poll_interval: 45
  repositories:
    - "owner/repo1"
  auto_approve_actions: false
  auto_fix_with_copilot: true

agents:
  enabled: true
  developer_enabled: true
  tester_enabled: false
  documentation_enabled: true
  project_manager_enabled: true

log_level: "DEBUG"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        config = PraierConfig.load_from_file(f.name)

        assert len(config.github_servers) == 1
        assert config.github_servers[0].name == "test"
        assert config.github_servers[0].token == "test-token"
        assert config.monitoring.poll_interval == 45
        assert config.monitoring.repositories == ["owner/repo1"]
        assert config.monitoring.auto_approve_actions is False
        assert config.monitoring.auto_fix_with_copilot is True
        assert config.agents.enabled is True
        assert config.agents.developer_enabled is True
        assert config.agents.tester_enabled is False
        assert config.agents.documentation_enabled is True
        assert config.agents.project_manager_enabled is True
        assert config.log_level == "DEBUG"

    # Clean up
    os.unlink(f.name)


def test_agent_config_from_env():
    """Test AgentConfig loading from environment variables."""
    os.environ["PRAIER_AGENTS_ENABLED"] = "true"
    os.environ["PRAIER_AGENT_DEVELOPER"] = "false"
    os.environ["PRAIER_AGENT_TESTER"] = "true"
    os.environ["PRAIER_AGENT_DOCUMENTATION"] = "true"
    os.environ["PRAIER_AGENT_PROJECT_MANAGER"] = "false"

    config = PraierConfig.load_from_env()

    assert config.agents.enabled is True
    assert config.agents.developer_enabled is False
    assert config.agents.tester_enabled is True
    assert config.agents.documentation_enabled is True
    assert config.agents.project_manager_enabled is False

    # Clean up
    del os.environ["PRAIER_AGENTS_ENABLED"]
    del os.environ["PRAIER_AGENT_DEVELOPER"]
    del os.environ["PRAIER_AGENT_TESTER"]
    del os.environ["PRAIER_AGENT_DOCUMENTATION"]
    del os.environ["PRAIER_AGENT_PROJECT_MANAGER"]


if __name__ == "__main__":
    test_github_config_from_env()
    test_github_config_defaults()
    test_praier_config_from_env()
    test_praier_config_from_yaml()
    test_agent_config_from_env()
    print("All configuration tests passed!")
