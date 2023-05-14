import click

from . import build, configure, schemas
from ._common import ProgramOptions, configure_logger

from .. import __version__


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context):
    '''A container orchestrator for homelabs.'''
    configure_logger()
    ctx.obj = ProgramOptions()


main.add_command(build.cmd)
main.add_command(configure.cmd)
main.add_command(schemas.cmd)
