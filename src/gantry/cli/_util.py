import logging
import sys

import click

from .._types import Path, PathLike
from ..exceptions import InvalidServiceDefinitionError
from ..logging import LOGGER_NAME
from ..services import ServiceGroupDefinition


def configure_logger() -> None:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(levelname)s :: %(message)s')
    ch.setFormatter(formatter)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ch)


def load_service_group(services_path: PathLike) -> ServiceGroupDefinition:
    try:
        return ServiceGroupDefinition(Path(services_path))
    except InvalidServiceDefinitionError as e:
        click.secho('Invalid Service Definition', fg='red', bold=True)
        for err in e.errors:
            click.echo(err)
        click.echo()
        raise click.ClickException('Failed to parse service group definition.')
