import click

from . import configure, schemas

from .. import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    '''A container orchestrator for homelabs.'''


main.add_command(configure.cmd)
main.add_command(schemas.cmd)
