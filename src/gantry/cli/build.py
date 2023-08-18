import datetime

import click

from ._common import ProgramOptions, load_service_group, print_header
from .._types import Path
from ..exceptions import CliException, ImageTargetException
from ..logging import get_app_logger
from ..targets import ImageTarget


def _check_mutually_exclusive_args(tag: str | None, build_number: int | None) -> None:
    has_tag = tag is not None
    has_build = build_number is not None

    if has_tag and has_build:
        raise CliException('Cannot specify both "--tag" and "--build-number".')


def _generate_version(tag: str | None, build_number: int | None) -> str:
    _check_mutually_exclusive_args(tag, build_number)

    if tag is not None:
        return tag

    id = 0
    if build_number is not None:
        id = build_number

    return f'{datetime.date.today():%Y%d%m}.{id}'


@click.command('build')
@click.option(
    '--tag', '-t',
    metavar='TAG',
    help=(
        'Specify the tag for the built image.  Specifying this overrides the '
        'auto-generated tag and cannot be used with "--build-number".'
    ),
    type=str
)
@click.option(
    '--build-number', '-n',
    metavar='BUILD',
    help=(
        'A build number that augments the auto-generated image version.  It '
        'cannot be used with "--tag".'
    ),
    type=int
)
@click.option(
    '--skip-build', '-s',
    is_flag=True,
    help=(
        'Skip the actual Docker build step.  This is useful if Docker will be '
        'called by another process and only the files are required.'
    )
)
@click.option(
    '--output', '-o', 'output_path',
    metavar='OUTPUT',
    help=(
        'Build folder that contains the Dockerfiles and associated files. '
        'This defaults to ./build/services.dockerfiles'
    ),
    default='./build/services.dockerfiles',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.argument(
    'services_path',
    metavar='PATH',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.pass_obj
def cmd(options: ProgramOptions,
        tag: str | None,
        build_number: int | None,
        skip_build: bool,
        output_path: Path,
        services_path: Path) -> None:
    '''Build the container images for a service group at PATH.

    A 'YYYYMMDD.###' tag will be automatically generated for the new image. This
    can be overriden with the "--tag" option.
    '''
    print_header()

    if config := options.config:
        namespace = config.registry_namespace
    else:
        get_app_logger().info('Performing image build without a gantry configuration.')
        namespace = None

    version = _generate_version(tag, build_number)
    service_group = load_service_group(services_path)
    try:
        ImageTarget(namespace, version, output_path, skip_build=skip_build).build(service_group)
    except ImageTargetException:
        raise CliException('Failed to build service images.')
