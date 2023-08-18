import click

import rich

from ._common import load_service_group, print_header

from .._types import Path
from ..exceptions import CliException, ComposeServiceBuildError
from ..targets import ComposeTarget


@click.command('configure')
@click.option(
    '--output', '-o',
    metavar='OUTPUT',
    help='Output folder for configured services.  Default is \'./build/services.[SERVICE]\'.',
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    '--force', '-f', 'force_overwrite',
    is_flag=True,
    help='Allow an existing output folder to be overwritten.'
)
@click.option(
    '--platform', '-p',
    metavar='PLATFORM',
    type=click.Choice(['compose'], case_sensitive=False),
    default='compose',
    help='The container orchestration platform.  Default is "compose".'
)
@click.argument(
    'services',
    metavar='PATH',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
def cmd(output: Path | None,
        force_overwrite: bool,
        platform: str,
        services: Path):
    '''Generate configurations that will deploy service containers.

    Services are deployed by converting a service group definition into the
    configurations for their equivalent targets.  The resulting configurations
    will be stored in the output directory specified by the '-o' option.
    '''
    if output is None:
        output = Path('./build') / f'services.{platform}'

    print_header()

    service_group = load_service_group(services)

    rich.print(f'Generating Docker Compose configuration at [blue bold]{output}[/blue bold].')

    try:
        ComposeTarget(output, force_overwrite).build(service_group)
    except ComposeServiceBuildError as e:
        raise CliException(str(e))
