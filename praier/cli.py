"""
Command-line interface for Praier.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .config import PraierConfig
from .monitor import PRMonitor


def setup_logging(log_level: str):
    """Configure logging for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


@click.group()
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to configuration file"
)
@click.option(
    "--log-level",
    "-l",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Set the logging level",
)
@click.pass_context
def cli(ctx, config: Optional[str], log_level: str):
    """Praier - Automate pull request workflows with GitHub Actions and Copilot."""
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        ctx.obj["config"] = PraierConfig.load_from_file(config)
    else:
        ctx.obj["config"] = PraierConfig.load_from_env()

    # Override log level if specified
    if log_level:
        ctx.obj["config"].log_level = log_level

    setup_logging(ctx.obj["config"].log_level)


@cli.command()
@click.pass_context
def monitor(ctx):
    """Start monitoring pull requests."""
    config = ctx.obj["config"]

    # Validate configuration
    if not any(server.token for server in config.github_servers):
        click.echo(
            "Error: No GitHub tokens configured. Set GITHUB_TOKEN environment "
            "variable or provide a config file.",
            err=True,
        )
        sys.exit(1)

    if not config.monitoring.repositories:
        click.echo(
            "Warning: No repositories configured for monitoring. Set "
            "PRAIER_REPOSITORIES environment variable.",
            err=True,
        )
        click.echo("Example: PRAIER_REPOSITORIES=owner/repo1,owner/repo2")
        sys.exit(1)

    click.echo("Starting Praier PR monitor...")
    click.echo(f"Poll interval: {config.monitoring.poll_interval} seconds")
    click.echo(f"Repositories: {', '.join(config.monitoring.repositories)}")
    click.echo(f"Auto-approve actions: {config.monitoring.auto_approve_actions}")
    click.echo(f"Auto-fix with Copilot: {config.monitoring.auto_fix_with_copilot}")

    # Start monitoring
    monitor_instance = PRMonitor(config)

    try:
        asyncio.run(monitor_instance.start_monitoring())
    except KeyboardInterrupt:
        click.echo("\nShutting down gracefully...")


@cli.command()
@click.pass_context
def status(ctx):
    """Show current monitoring status."""
    config = ctx.obj["config"]

    click.echo("Praier Configuration Status")
    click.echo("=" * 30)

    # GitHub servers
    click.echo(f"GitHub Servers: {len(config.github_servers)}")
    for i, server in enumerate(config.github_servers):
        token_status = "✓" if server.token else "✗"
        click.echo(f"  {i + 1}. {server.name} ({server.url}) - Token: {token_status}")

    # Monitoring config
    click.echo("\nMonitoring Configuration:")
    click.echo(f"  Poll interval: {config.monitoring.poll_interval}s")
    click.echo(
        f"  Max concurrent requests: {config.monitoring.max_concurrent_requests}"
    )
    click.echo(f"  Auto-approve actions: {config.monitoring.auto_approve_actions}")
    click.echo(f"  Auto-fix with Copilot: {config.monitoring.auto_fix_with_copilot}")

    # Repositories
    if config.monitoring.repositories:
        click.echo(f"\nRepositories ({len(config.monitoring.repositories)}):")
        for repo in config.monitoring.repositories:
            click.echo(f"  - {repo}")
    else:
        click.echo("\nRepositories: None configured")

    click.echo(f"\nLog level: {config.log_level}")


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def generate_config(output: Optional[str]):
    """Generate a sample configuration file."""
    config_content = """# Praier Configuration File
# Copy this file and customize it for your needs

github_servers:
  - name: "public"
    url: "https://api.github.com"
    token: "${GITHUB_TOKEN}"

  # Example for GitHub Enterprise Server
  # - name: "enterprise"
  #   url: "https://github.company.com/api/v3"
  #   token: "${GITHUB_ENTERPRISE_TOKEN}"

monitoring:
  poll_interval: 60  # seconds
  max_concurrent_requests: 10
  repositories:
    - "owner/repo1"
    - "owner/repo2"
  auto_approve_actions: true
  auto_fix_with_copilot: true

log_level: "INFO"
"""

    if output:
        output_path = Path(output)
        output_path.write_text(config_content)
        click.echo(f"Sample configuration written to {output_path}")
    else:
        click.echo(config_content)


@cli.command()
@click.argument("repository")
@click.option("--server", "-s", default="default", help="GitHub server name")
@click.pass_context
def test_connection(ctx, repository: str, server: str):
    """Test connection to GitHub and list PRs for a repository."""
    config = ctx.obj["config"]

    # Find the specified server
    github_config = None
    for srv in config.github_servers:
        if srv.name == server:
            github_config = srv
            break

    if not github_config:
        click.echo(f"Error: Server '{server}' not found in configuration", err=True)
        sys.exit(1)

    if not github_config.token:
        click.echo(f"Error: No token configured for server '{server}'", err=True)
        sys.exit(1)

    from .github_client import GitHubClient

    try:
        client = GitHubClient(github_config.url, github_config.token)
        click.echo(f"Testing connection to {github_config.url}...")

        prs = client.get_pull_requests(repository)

        click.echo(f"✓ Successfully connected to {github_config.name}")
        click.echo(f"Found {len(prs)} open pull requests in {repository}:")

        for pr in prs[:5]:  # Show first 5 PRs
            click.echo(f"  #{pr.number}: {pr.title} ({pr.author})")

        if len(prs) > 5:
            click.echo(f"  ... and {len(prs) - 5} more")

    except Exception as e:
        click.echo(f"✗ Connection failed: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
