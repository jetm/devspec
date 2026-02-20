import click

from devspec import __version__


@click.group()
@click.version_option(version=__version__, prog_name="devspec")
def cli():
    """Spec-driven development workflow engine."""


def main():
    cli()
