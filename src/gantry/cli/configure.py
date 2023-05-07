import click

from .._types import Path
from ..build import build_services
from ..exceptions import ComposeServiceBuildError, InvalidServiceDefinitionError
from ..services import ServiceGroupDefinition


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
    try:
        service_group = ServiceGroupDefinition(services)
    except InvalidServiceDefinitionError as e:
        click.secho('Invalid Service Definition', fg='red', bold=True)
        for err in e.errors:
            click.echo(err)
        click.echo()
        raise click.ClickException('Failed to parse service group definition.')

    try:
        build_services(service_group, output, overwrite=force_overwrite)
    except ComposeServiceBuildError as e:
        raise click.ClickException(str(e))