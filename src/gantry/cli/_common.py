from typing import NamedTuple

import click

import rich

from .._types import Path, PathLike
from ..config import Config
from ..exceptions import InvalidServiceDefinitionError
from ..services import ServiceGroupDefinition


class ProgramOptions(NamedTuple):
    app_folder: Path
    '''The location where the program's runtime data is stored.'''

    config: Config | None
    '''The program's configuration data.  Will be "None" if it isn't available.'''


def load_service_group(services_path: PathLike) -> ServiceGroupDefinition:
    try:
        return ServiceGroupDefinition(Path(services_path))
    except InvalidServiceDefinitionError as e:
        click.secho('Invalid Service Definition', fg='red', bold=True)
        for err in e.errors:
            click.echo(err)
        click.echo()
        raise click.ClickException('Failed to parse service group definition.')


def print_header() -> None:
    from .. import __version__
    console = rich.get_console()
    console.print(f'[bold]gantry {__version__}[/bold]', highlight=False)
