import logging
from typing import Any

import click

from . import build, configure, schemas
from ._common import ProgramOptions

from .. import __version__
from .._types import Path
from ..logging import init_logger


@click.group()
@click.option('--debug', '-d', help='Enable debugging output.', is_flag=True)
@click.option(
    '--logfile', '-l',
    help='Log to a file.',
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path)
)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context, debug: bool, logfile: Path | None) -> None:
    '''A container orchestrator for homelabs.'''
    logging_args: dict[str, Any] = {
        'logfile': logfile
    }

    if debug:
        logging_args['log_level'] = logging.DEBUG
        logging_args['show_traceback'] = True

    init_logger(**logging_args)  # type: ignore
    ctx.obj = ProgramOptions()


main.add_command(build.cmd)
main.add_command(configure.cmd)
main.add_command(schemas.cmd)
