"""
GitHub client for GraphQL and REST API interactions.
"""

import json
import logging
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class PullRequest:
    """Represents a pull request."""
    
    id: str
    number: int
    title: str
    url: str
    state: str
    head_sha: str
    base_ref: str
    head_ref: str
    author: str
    repository: str
    created_at: datetime
    updated_at: datetime
    mergeable: Optional[bool] = None
    draft: bool = False


@dataclass
class CheckRun:
    """Represents a GitHub Actions check run."""
    
    id: str
    name: str
    status: str  # queued, in_progress, completed
    conclusion: Optional[str]  # success, failure, neutral, cancelled, skipped, timed_out, action_required
    url: str
    pull_request_number: Optional[int] = None


@dataclass
class WorkflowRun:
    """Represents a GitHub Actions workflow run."""
    
    id: str
    name: str
    status: str
    conclusion: Optional[str]
    url: str
    head_sha: str
    pull_requests: List[int] = None
    
    def __post_init__(self):
        if self.pull_requests is None:
            self.pull_requests = []


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'praier/0.1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated request to the GitHub API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code == 401:
            logger.error("GitHub authentication failed. Check your token.")
            raise requests.exceptions.HTTPError("Authentication failed")
        
        response.raise_for_status()
        return response
    
    def graphql_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        if variables is None:
            variables = {}
        
        payload = {
            'query': query,
            'variables': variables
        }
        
        response = self._make_request('POST', '/graphql', json=payload)
        data = response.json()
        
        if 'errors' in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise ValueError(f"GraphQL query failed: {data['errors']}")
        
        return data['data']
    
    def get_pull_requests(self, repository: str, state: str = "open") -> List[PullRequest]:
        """Get pull requests for a repository using GraphQL."""
        owner, repo = repository.split('/')
        
        query = """
        query($owner: String!, $repo: String!, $states: [PullRequestState!], $first: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequests(states: $states, first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes {
                id
                number
                title
                url
                state
                headRefOid
                baseRefName
                headRefName
                author {
                  login
                }
                createdAt
                updatedAt
                mergeable
                isDraft
              }
            }
          }
        }
        """
        
        variables = {
            'owner': owner,
            'repo': repo,
            'states': [state.upper()],
            'first': 100
        }
        
        data = self.graphql_query(query, variables)
        prs = []
        
        for pr_data in data['repository']['pullRequests']['nodes']:
            pr = PullRequest(
                id=pr_data['id'],
                number=pr_data['number'],
                title=pr_data['title'],
                url=pr_data['url'],
                state=pr_data['state'].lower(),
                head_sha=pr_data['headRefOid'],
                base_ref=pr_data['baseRefName'],
                head_ref=pr_data['headRefName'],
                author=pr_data['author']['login'] if pr_data['author'] else 'unknown',
                repository=repository,
                created_at=datetime.fromisoformat(pr_data['createdAt'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(pr_data['updatedAt'].replace('Z', '+00:00')),
                mergeable=pr_data['mergeable'],
                draft=pr_data['isDraft']
            )
            prs.append(pr)
        
        return prs
    
    def get_workflow_runs(self, repository: str, head_sha: str = None) -> List[WorkflowRun]:
        """Get workflow runs for a repository."""
        owner, repo = repository.split('/')
        endpoint = f"/repos/{owner}/{repo}/actions/runs"
        
        params = {'per_page': 100}
        if head_sha:
            params['head_sha'] = head_sha
        
        response = self._make_request('GET', endpoint, params=params)
        data = response.json()
        
        runs = []
        for run_data in data['workflow_runs']:
            pr_numbers = [pr['number'] for pr in run_data.get('pull_requests', [])]
            
            run = WorkflowRun(
                id=str(run_data['id']),
                name=run_data['name'],
                status=run_data['status'],
                conclusion=run_data['conclusion'],
                url=run_data['html_url'],
                head_sha=run_data['head_sha'],
                pull_requests=pr_numbers
            )
            runs.append(run)
        
        return runs
    
    def approve_workflow_run(self, repository: str, run_id: str) -> bool:
        """Approve a workflow run that requires approval."""
        owner, repo = repository.split('/')
        endpoint = f"/repos/{owner}/{repo}/actions/runs/{run_id}/approve"
        
        try:
            response = self._make_request('POST', endpoint)
            logger.info(f"Approved workflow run {run_id} in {repository}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Workflow run {run_id} not found or already approved")
            else:
                logger.error(f"Failed to approve workflow run {run_id}: {e}")
            return False
    
    def get_check_runs(self, repository: str, ref: str) -> List[CheckRun]:
        """Get check runs for a specific commit."""
        owner, repo = repository.split('/')
        endpoint = f"/repos/{owner}/{repo}/commits/{ref}/check-runs"
        
        response = self._make_request('GET', endpoint)
        data = response.json()
        
        check_runs = []
        for check_data in data['check_runs']:
            check_run = CheckRun(
                id=str(check_data['id']),
                name=check_data['name'],
                status=check_data['status'],
                conclusion=check_data['conclusion'],
                url=check_data['html_url']
            )
            check_runs.append(check_run)
        
        return check_runs
    
    def create_issue_comment(self, repository: str, issue_number: int, body: str) -> bool:
        """Create a comment on an issue or pull request."""
        owner, repo = repository.split('/')
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        
        payload = {'body': body}
        
        try:
            response = self._make_request('POST', endpoint, json=payload)
            logger.info(f"Created comment on PR #{issue_number} in {repository}")
            return True
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to create comment on PR #{issue_number}: {e}")
            return False
    
    def request_copilot_fix(self, repository: str, pr_number: int, failing_checks: List[CheckRun]) -> bool:
        """Request GitHub Copilot to fix failing checks in a PR."""
        # Create a comment that triggers Copilot to analyze and fix the PR
        check_names = [check.name for check in failing_checks]
        
        comment_body = f"""@copilot The following checks are failing in this PR:

{chr(10).join(f'- {name}' for name in check_names)}

Please analyze the failing checks and suggest fixes for the issues. Focus on:
1. Test failures and their root causes
2. Linting/formatting issues
3. Build failures
4. Security vulnerabilities

Provide specific code changes that would resolve these issues."""
        
        return self.create_issue_comment(repository, pr_number, comment_body)