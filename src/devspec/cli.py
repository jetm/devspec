import click

from devspec import __version__
from devspec.commands.analyze import analyze
from devspec.commands.archive import archive
from devspec.commands.ask import ask
from devspec.commands.context import context
from devspec.commands.handoff import handoff
from devspec.commands.init import init
from devspec.commands.instructions import instructions
from devspec.commands.list import list_changes
from devspec.commands.migrate import migrate
from devspec.commands.new import new
from devspec.commands.preflight import preflight
from devspec.commands.status import status
from devspec.commands.validate import validate


@click.group()
@click.version_option(version=__version__, prog_name="devspec")
def cli():
    """Spec-driven development workflow engine."""


cli.add_command(analyze)
cli.add_command(ask)
cli.add_command(init)
cli.add_command(migrate)
cli.add_command(new)
cli.add_command(status)
cli.add_command(instructions)
cli.add_command(list_changes)
cli.add_command(archive)
cli.add_command(preflight)
cli.add_command(validate)
cli.add_command(context)
cli.add_command(handoff)


def main():
    cli()
