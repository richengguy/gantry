import click

from .._types import ProgramOptions


def _check_mutually_exclusive_args(tag: str | None, build_number: int | None) -> None:
    has_tag = tag is not None
    has_build = build_number is not None

    if has_tag and has_build:
        raise click.ClickException('Cannot specify both "--tag" and "--build-number".')


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
    _check_mutually_exclusive_args(tag, build_number)
