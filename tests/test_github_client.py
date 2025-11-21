"""
Tests for the GitHub client module.
"""

from datetime import datetime

from praier.github_client import CheckRun, PullRequest, WorkflowRun


def test_pull_request_creation():
    """Test PullRequest dataclass creation."""
    pr = PullRequest(
        id="MDExOlB1bGxSZXF1ZXN0Nzk5NTI4NTEx",
        number=123,
        title="Test PR",
        url="https://github.com/owner/repo/pull/123",
        state="open",
        head_sha="abc123",
        base_ref="main",
        head_ref="feature-branch",
        author="testuser",
        repository="owner/repo",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        draft=False,
    )

    assert pr.number == 123
    assert pr.title == "Test PR"
    assert pr.state == "open"
    assert pr.repository == "owner/repo"
    assert pr.draft == False


def test_check_run_creation():
    """Test CheckRun dataclass creation."""
    check = CheckRun(
        id="12345",
        name="CI Tests",
        status="completed",
        conclusion="failure",
        url="https://github.com/owner/repo/runs/12345",
    )

    assert check.id == "12345"
    assert check.name == "CI Tests"
    assert check.status == "completed"
    assert check.conclusion == "failure"


def test_workflow_run_creation():
    """Test WorkflowRun dataclass creation."""
    run = WorkflowRun(
        id="67890",
        name="CI",
        status="completed",
        conclusion="success",
        url="https://github.com/owner/repo/actions/runs/67890",
        head_sha="def456",
        pull_requests=[123, 124],
    )

    assert run.id == "67890"
    assert run.name == "CI"
    assert run.pull_requests == [123, 124]


def test_workflow_run_defaults():
    """Test WorkflowRun defaults."""
    run = WorkflowRun(
        id="67890",
        name="CI",
        status="in_progress",
        conclusion=None,
        url="https://github.com/owner/repo/actions/runs/67890",
        head_sha="def456",
    )

    assert run.pull_requests == []


if __name__ == "__main__":
    test_pull_request_creation()
    test_check_run_creation()
    test_workflow_run_creation()
    test_workflow_run_defaults()
    print("All GitHub client tests passed!")
