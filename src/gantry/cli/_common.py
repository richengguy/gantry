from typing import NamedTuple

import click

from .._types import Path, PathLike
from ..exceptions import InvalidServiceDefinitionError
from ..services import ServiceGroupDefinition


class ProgramOptions(NamedTuple):
    ...


def load_service_group(services_path: PathLike) -> ServiceGroupDefinition:
    try:
        return ServiceGroupDefinition(Path(services_path))
    except InvalidServiceDefinitionError as e:
        click.secho('Invalid Service Definition', fg='red', bold=True)
        for err in e.errors:
            click.echo(err)
        click.echo()
        raise click.ClickException('Failed to parse service group definition.')
