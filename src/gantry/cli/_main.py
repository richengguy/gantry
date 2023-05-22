import logging
from typing import Any

import click

import rich

from . import build, configure, forge, schemas
from ._common import ProgramOptions

from .. import __version__
from .._types import Path
from ..config import Config
from ..exceptions import ConfigException, CliException
from ..logging import init_logger


def _load_config_file(config_file: Path) -> Config | None:
    if not config_file.exists():
        return None

    try:
        return Config(config_file)
    except ConfigException as exc:
        rich.print(exc)
        raise CliException(f'Failed to load {config_file}.') from exc


@click.group()
@click.option(
    '--app-folder', '-a', 'app_folder',
    help='Gantry application folder.',
    default='.gantry',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    '--config', '-c', 'config_file',
    help='Gantry configuration file.',
    default='gantry.yml',
    type=click.Path(file_okay=True, dir_okay=False, exists=False, path_type=Path)
)
@click.option('--debug', '-d', help='Enable debugging output.', is_flag=True)
@click.option(
    '--logfile', '-l',
    help='Log to a file.',
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path)
)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context,
         app_folder: Path,
         config_file: Path,
         debug: bool,
         logfile: Path | None) -> None:
    '''A container orchestrator for homelabs.'''
    logging_args: dict[str, Any] = {
        'logfile': logfile
    }

    if debug:
        logging_args['log_level'] = logging.DEBUG
        logging_args['show_traceback'] = True

    logger = init_logger(**logging_args)  # type: ignore
    ctx.obj = ProgramOptions(
        app_folder=app_folder,
        config=_load_config_file(config_file)
    )

    if not app_folder.exists():
        logger.debug('Creating app folder at \'%s\'.', app_folder)
        app_folder.mkdir(mode=0o700, parents=True)


main.add_command(build.cmd)
main.add_command(configure.cmd)
main.add_command(forge.cmd)
main.add_command(schemas.cmd)
