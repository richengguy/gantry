import click

import rich

from ._common import load_service_group, print_header

from .._types import Path
from ..exceptions import CliException, ComposeServiceBuildError
from ..targets import ComposeTarget


@click.group('configure')
def cmd():
    '''Generate configurations that will deploy service containers.

    Services are deployed by converting a service group definition into the
    configurations for their equivalent targets.
    '''


@cmd.command('compose')
@click.option('--services', '-s', default='./services',
              help='Folder containing the service definitions. Default is \'./services\'.',
              type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--output', '-o', default='./services.docker',
              help='Output folder for Compose services.  Default is \'./services.docker\'.',
              type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--force', '-f', 'force_overwrite', is_flag=True,
              help='Allow an existing output folder to be overwritten.')
def cmd_compose(services: Path, output: Path, force_overwrite: bool):
    '''Generate a Docker Compose configuration.

    The Compose configuration will generate a folder for everything needed to
    bring up all services on a Docker host.  The folder just needs to be placed
    onto the host and then started with `docker compose up -d`.'''
    print_header()

    service_group = load_service_group(services)

    rich.print(f'Generating Docker Compose configuration at [blue bold]{output}[/blue bold].')

    try:
        ComposeTarget(output, force_overwrite).build(service_group)
    except ComposeServiceBuildError as e:
        raise CliException(str(e))
