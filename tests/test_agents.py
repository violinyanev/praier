"""
Tests for the agent system.
"""

from datetime import datetime

import pytest

from praier.agents import (
    Agent,
    AgentReport,
    AgentTeam,
    DeveloperAgent,
    DocumentationAgent,
    ProjectManagerAgent,
    TesterAgent,
    create_default_team,
)
from praier.github_client import CheckRun, PullRequest, WorkflowRun


@pytest.fixture
def sample_pr():
    """Create a sample pull request."""
    return PullRequest(
        id="PR123",
        number=42,
        title="Add new feature",
        url="https://github.com/owner/repo/pull/42",
        state="open",
        head_sha="abc123",
        base_ref="main",
        head_ref="feature",
        author="developer",
        repository="owner/repo",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        draft=False,
    )


@pytest.fixture
def failing_test_checks():
    """Create sample failing test checks."""
    return [
        CheckRun(
            id="check1",
            name="Unit Tests",
            status="completed",
            conclusion="failure",
            url="https://github.com/owner/repo/runs/check1",
        ),
        CheckRun(
            id="check2",
            name="Integration Tests",
            status="completed",
            conclusion="failure",
            url="https://github.com/owner/repo/runs/check2",
        ),
    ]


@pytest.fixture
def passing_checks():
    """Create sample passing checks."""
    return [
        CheckRun(
            id="check3",
            name="Lint Check",
            status="completed",
            conclusion="success",
            url="https://github.com/owner/repo/runs/check3",
        ),
    ]


@pytest.fixture
def failing_lint_checks():
    """Create sample failing lint checks."""
    return [
        CheckRun(
            id="check4",
            name="Lint",
            status="completed",
            conclusion="failure",
            url="https://github.com/owner/repo/runs/check4",
        ),
    ]


@pytest.fixture
def workflow_runs():
    """Create sample workflow runs."""
    return [
        WorkflowRun(
            id="run1",
            name="CI",
            status="completed",
            conclusion="success",
            url="https://github.com/owner/repo/actions/runs/run1",
            head_sha="abc123",
            pull_requests=[42],
        ),
    ]


@pytest.mark.asyncio
async def test_developer_agent_clean_code(sample_pr, passing_checks, workflow_runs):
    """Test developer agent with clean code."""
    agent = DeveloperAgent()
    report = await agent.analyze(sample_pr, "owner/repo", passing_checks, workflow_runs)

    assert report.agent_name == "Developer"
    assert report.pr_number == 42
    assert report.priority == "low"
    assert "good shape" in report.summary.lower()


@pytest.mark.asyncio
async def test_developer_agent_code_quality_issues(
    sample_pr, failing_lint_checks, workflow_runs
):
    """Test developer agent detecting code quality issues."""
    agent = DeveloperAgent()
    report = await agent.analyze(
        sample_pr, "owner/repo", failing_lint_checks, workflow_runs
    )

    assert report.agent_name == "Developer"
    assert report.priority == "high"
    assert any("quality" in finding.lower() for finding in report.findings)
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_developer_agent_draft_pr(sample_pr, passing_checks, workflow_runs):
    """Test developer agent with draft PR."""
    sample_pr.draft = True
    agent = DeveloperAgent()
    report = await agent.analyze(sample_pr, "owner/repo", passing_checks, workflow_runs)

    assert any("draft" in finding.lower() for finding in report.findings)
    assert any("ready for review" in rec.lower() for rec in report.recommendations)


@pytest.mark.asyncio
async def test_tester_agent_failing_tests(
    sample_pr, failing_test_checks, workflow_runs
):
    """Test tester agent detecting failing tests."""
    agent = TesterAgent()
    report = await agent.analyze(
        sample_pr, "owner/repo", failing_test_checks, workflow_runs
    )

    assert report.agent_name == "Tester"
    assert report.priority == "critical"
    assert "failing test" in report.summary.lower()
    assert len(report.findings) > 0


@pytest.mark.asyncio
async def test_tester_agent_passing_tests(sample_pr, passing_checks, workflow_runs):
    """Test tester agent with passing tests."""
    # Create test-specific passing check
    test_checks = [
        CheckRun(
            id="test1",
            name="pytest",
            status="completed",
            conclusion="success",
            url="https://github.com/owner/repo/runs/test1",
        ),
    ]

    agent = TesterAgent()
    report = await agent.analyze(sample_pr, "owner/repo", test_checks, workflow_runs)

    assert report.priority == "low"
    assert "passing" in report.summary.lower()


@pytest.mark.asyncio
async def test_tester_agent_no_tests(sample_pr, passing_checks, workflow_runs):
    """Test tester agent when no test checks are present."""
    agent = TesterAgent()
    report = await agent.analyze(sample_pr, "owner/repo", passing_checks, workflow_runs)

    assert "no test checks detected" in report.summary.lower()
    assert any("add automated tests" in rec.lower() for rec in report.recommendations)


@pytest.mark.asyncio
async def test_documentation_agent_no_checks(sample_pr, passing_checks, workflow_runs):
    """Test documentation agent with no doc checks."""
    agent = DocumentationAgent()
    report = await agent.analyze(sample_pr, "owner/repo", passing_checks, workflow_runs)

    assert "no documentation checks" in report.summary.lower()
    assert report.priority == "low"


@pytest.mark.asyncio
async def test_documentation_agent_short_title(
    sample_pr, passing_checks, workflow_runs
):
    """Test documentation agent detecting short PR title."""
    sample_pr.title = "Fix"  # Very short title
    agent = DocumentationAgent()
    report = await agent.analyze(sample_pr, "owner/repo", passing_checks, workflow_runs)

    assert any("title" in finding.lower() for finding in report.findings)


@pytest.mark.asyncio
async def test_project_manager_agent_overview(
    sample_pr, failing_test_checks, workflow_runs
):
    """Test project manager agent providing overview."""
    agent = ProjectManagerAgent()
    report = await agent.analyze(
        sample_pr, "owner/repo", failing_test_checks, workflow_runs
    )

    assert report.agent_name == "ProjectManager"
    assert any("total checks" in finding.lower() for finding in report.findings)
    assert "failing" in report.summary.lower()


@pytest.mark.asyncio
async def test_project_manager_agent_all_passing(
    sample_pr, passing_checks, workflow_runs
):
    """Test project manager with all checks passing."""
    agent = ProjectManagerAgent()
    report = await agent.analyze(sample_pr, "owner/repo", passing_checks, workflow_runs)

    assert report.priority == "low"
    assert "ready" in report.summary.lower()


def test_agent_enable_disable():
    """Test enabling and disabling agents."""
    agent = DeveloperAgent()

    assert agent.is_enabled()

    agent.disable()
    assert not agent.is_enabled()

    agent.enable()
    assert agent.is_enabled()


def test_agent_team_creation():
    """Test creating an agent team."""
    team = AgentTeam()

    assert len(team.list_agents()) == 0

    developer = DeveloperAgent()
    team.add_agent(developer)

    assert len(team.list_agents()) == 1
    assert "Developer" in team.list_agents()


def test_agent_team_remove_agent():
    """Test removing an agent from the team."""
    team = create_default_team()
    initial_count = len(team.list_agents())

    team.remove_agent("Developer")

    assert len(team.list_agents()) == initial_count - 1
    assert "Developer" not in team.list_agents()


def test_agent_team_get_agent():
    """Test getting a specific agent."""
    team = create_default_team()

    agent = team.get_agent("Developer")
    assert agent is not None
    assert agent.name == "Developer"

    non_existent = team.get_agent("NonExistent")
    assert non_existent is None


@pytest.mark.asyncio
async def test_agent_team_analyze_pr(sample_pr, failing_test_checks, workflow_runs):
    """Test agent team analyzing a PR."""
    team = create_default_team()

    reports = await team.analyze_pr(
        sample_pr, "owner/repo", failing_test_checks, workflow_runs
    )

    assert len(reports) == 4  # All 4 agents should report
    assert "Developer" in reports
    assert "Tester" in reports
    assert "Documentation" in reports
    assert "ProjectManager" in reports


@pytest.mark.asyncio
async def test_agent_team_with_disabled_agent(
    sample_pr, failing_test_checks, workflow_runs
):
    """Test agent team with a disabled agent."""
    team = create_default_team()

    # Disable the developer agent
    developer = team.get_agent("Developer")
    developer.disable()

    reports = await team.analyze_pr(
        sample_pr, "owner/repo", failing_test_checks, workflow_runs
    )

    assert len(reports) == 3  # Only 3 enabled agents should report
    assert "Developer" not in reports


def test_agent_team_summary():
    """Test generating a team summary from reports."""
    team = create_default_team()

    # Create mock reports
    reports = {
        "Developer": AgentReport(
            agent_name="Developer",
            pr_number=42,
            repository="owner/repo",
            summary="All good",
            findings=["Finding 1", "Finding 2"],
            recommendations=["Rec 1"],
            priority="low",
        ),
        "Tester": AgentReport(
            agent_name="Tester",
            pr_number=42,
            repository="owner/repo",
            summary="Tests failing",
            findings=["Test failure"],
            recommendations=["Fix tests"],
            priority="critical",
        ),
    }

    summary = team.get_team_summary(reports)

    assert summary["total_agents"] == 4  # Team has 4 agents
    assert summary["active_agents"] == 2  # 2 reports provided
    assert summary["total_findings"] == 3  # 2 + 1
    assert summary["total_recommendations"] == 2  # 1 + 1
    assert summary["overall_priority"] == "critical"  # Highest priority


def test_create_default_team():
    """Test creating the default agent team."""
    team = create_default_team()

    assert len(team.list_agents()) == 4
    assert "Developer" in team.list_agents()
    assert "Tester" in team.list_agents()
    assert "Documentation" in team.list_agents()
    assert "ProjectManager" in team.list_agents()


def test_agent_report_creation():
    """Test creating an agent report."""
    report = AgentReport(
        agent_name="TestAgent",
        pr_number=123,
        repository="owner/repo",
        summary="Test summary",
        findings=["Finding 1"],
        recommendations=["Rec 1"],
        actions_taken=["Action 1"],
        priority="high",
    )

    assert report.agent_name == "TestAgent"
    assert report.pr_number == 123
    assert report.priority == "high"
    assert len(report.findings) == 1
    assert len(report.recommendations) == 1
    assert len(report.actions_taken) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
