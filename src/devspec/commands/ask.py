import click

from devspec.tui.ask_app import run_ask_app


@click.command()
@click.option("--session", required=True, help="Session ID to load questions from")
def ask(session: str) -> None:
    """Present structured questions via TUI."""
    run_ask_app(session)


def main() -> None:
    ask()
