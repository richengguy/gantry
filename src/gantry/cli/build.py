import datetime

import click

from ._util import load_service_group
from .._types import Path, ProgramOptions
from ..targets import ImageTarget


def _check_mutually_exclusive_args(tag: str | None, build_number: int | None) -> None:
    has_tag = tag is not None
    has_build = build_number is not None

    if has_tag and has_build:
        raise click.ClickException('Cannot specify both "--tag" and "--build-number".')


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
@click.argument('services', metavar='[SERVICE]...', nargs=-1)
@click.pass_obj
def cmd(options: ProgramOptions,
        tag: str | None,
        build_number: int | None,
        services: tuple[str]) -> None:
    '''Build a SERVICE container image.

    By default, the command will build images for all services. Specifying the
    individual SERVICE will build just that image.  A 'YYYYMMDD.###' tag will be
    automatically generated for the new image, though this can be overriden with
    the "--tag" option.
    '''
    version = _generate_version(tag, build_number)
    service_group = load_service_group(options.services_path)
    ImageTarget('abc', version, Path('./build/test')).build(service_group)
