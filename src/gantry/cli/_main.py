import logging
import sys

import click

from . import build, configure, schemas

from .. import __version__
from .._types import Path, ProgramOptions
from ..logging import LOGGER_NAME


def _configure_logger() -> None:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(levelname)s :: %(message)s')
    ch.setFormatter(formatter)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ch)


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
    _configure_logger()

    ctx.obj = ProgramOptions(services_path=services_path)


main.add_command(build.cmd)
main.add_command(configure.cmd)
main.add_command(schemas.cmd)
