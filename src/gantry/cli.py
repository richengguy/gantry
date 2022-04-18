from pathlib import Path

import click

from . import ServiceGroupDefinition
from .build import build_services
from .exceptions import ComposeServiceBuildError, InvalidServiceDefinitionError


@click.group()
@click.version_option()
def main():
    '''Manage containers on single-host systems.'''
    pass


@main.command()
@click.option('--services', '-s', default='./services',
              help='Folder containing the service definitions. Default is \'./services\'.',
              type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--output', '-o', default='./services.docker',
              help='Output folder for Compose services.  Default is \'./services.docker\'.',
              type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--force', '-f', 'force_overwrite', is_flag=True,
              help='Allow an existing output folder to be overwritten.')
def build_compose(services: Path, output: Path, force_overwrite: bool):
    '''Build a Docker Compose specification from a service group.'''
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


if __name__ == '__main__':
    main()
