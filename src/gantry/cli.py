import json
from pathlib import Path

import click

from . import ServiceGroupDefinition, __version__
from .build import build_services
from .exceptions import ComposeServiceBuildError, InvalidServiceDefinitionError
from .schemas import get_schema, Schema


@click.group()
@click.version_option(version=__version__)
def main():
    '''Manage containers on single-host systems.'''


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


@main.group()
def schemas():
    '''Access the schemas that validate service groups and definitions.'''


@schemas.command('dump')
@click.argument('name', metavar='NAME',
                type=click.Choice([schema.value for schema in Schema]))
def schemas_dump(name: str):
    '''Prints a schema in JSON format to stdout.

    The list of valid schema names can be found with `gantry schemas list`.
    '''
    schema = Schema(name)
    contents = get_schema(schema)
    click.echo(json.dumps(contents, indent=4))


@schemas.command('export')
@click.option('--output', '-o', default='./schemas',
              type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
              help='Output folder for the schema files.  Defaults to \'./schemas\'.')
def schemas_export(output: Path):
    '''Export the JSON schema files used by gantry.'''
    output.mkdir(exist_ok=True)
    for schema in Schema:
        contents = get_schema(schema)
        with (output / f'{schema.value}.json').open('wt') as f:
            json.dump(contents, f, indent=4)


@schemas.command('list')
def schemas_list():
    '''List the schemas used by gantry.'''
    for schema in Schema:
        click.echo(schema.value)


if __name__ == '__main__':
    main()
