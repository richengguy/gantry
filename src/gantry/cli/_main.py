import click

from . import build, configure, schemas
from ._common import ProgramOptions, configure_logger

from .. import __version__
from .._types import Path


@click.group()
@click.option(
    '--service-group', '-s', 'services_path',
    metavar='PATH',
    help='Path to the service group definition folder.  Defaults to "./services".',
    default='./services',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context, services_path: Path):
    '''A container orchestrator for homelabs.'''
    configure_logger()
    ctx.obj = ProgramOptions(services_path=services_path)


main.add_command(build.cmd)
main.add_command(configure.cmd)
main.add_command(schemas.cmd)
