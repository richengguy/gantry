import datetime
from typing import Callable, NamedTuple, Type

import click

from rich import box
from rich.console import Console
from rich.table import Table

from ._common import ProgramOptions, load_service_group, print_header
from .._types import Path
from ..config import Config
from ..exceptions import CliException, GantryException
from ..logging import get_app_logger
from ..services import ServiceGroupDefinition
from ..targets import ComposeTarget, ImageTarget, Target


class BuildTargetInfo(NamedTuple):
    target_type: Type[Target]
    callback: Callable[[ServiceGroupDefinition, Config | None, str, Path, list[str]], None]


def _build_compose(service_group: ServiceGroupDefinition,
                   config: Config | None,
                   version: str,
                   output: Path,
                   options: list[str]) -> None:
    console = Console()
    console.print(f'Generating Docker Compose configuration at [blue bold]{output}[/blue bold].')
    ComposeTarget(output, options=options).build(service_group)


def _build_image(service_group: ServiceGroupDefinition,
                 config: Config | None,
                 version: str,
                 output: Path,
                 options: list[str]) -> None:
    if config is not None:
        namespace = config.registry_namespace
    else:
        get_app_logger().info('Performing image build without a gantry configuration.')
        namespace = None

    console = Console()
    console.print(f'Building container images for [blue bold]{service_group.folder}[/blue bold].')
    ImageTarget(namespace, version, output, options=options).build(service_group)


TARGETS: dict[str, 'BuildTargetInfo'] = {
    'compose': BuildTargetInfo(ComposeTarget, _build_compose),
    'image': BuildTargetInfo(ImageTarget, _build_image)
}


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


def _list_targets(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return

    console = Console()

    for name, (target, _) in TARGETS.items():
        header = Table(width=80, box=None, show_header=False)
        header.add_column(width=16)
        header.add_column()
        header.add_row(f'[b]\'{name}\'[/b]', f'[i]{target.description()}[/i]')
        console.print(header)

        table = Table(width=80, box=box.ROUNDED, show_lines=True)
        table.add_column('Option')
        table.add_column('Description')
        for opt, desc in target.options():
            table.add_row(opt, desc)

        if table.row_count > 0:
            console.print(table)
        else:
            empty = Table(width=80, box=None, show_header=False)
            empty.add_column(width=16)
            empty.add_column()
            empty.add_row('[grey50]No Options[/grey50]', '')
            console.print(empty)

        console.print()

    ctx.exit()


@click.command('build')
@click.option(
    '--tag', '-t',
    metavar='TAG',
    help=(
        'Provide a tag to identify the build artifact.  Specifying this '
        'overrides the auto-generated tag and cannot be used with '
        '"--build-number".'
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
    '--list-targets',
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_list_targets,
    help='List all of the available build targets.'
)
@click.option(
    '--output', '-o', 'output_path',
    metavar='OUTPUT',
    help='The folder that will hold the build artifacts.',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    '--target-option', '-X', 'extra_options',
    type=str,
    multiple=True,
    help='Pass in a target-specific option.'
)
@click.argument('target', nargs=1, type=str)
@click.argument(
    'services_path',
    metavar='SERVICE_GROUP',
    nargs=1,
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path)
)
@click.pass_obj
def cmd(opts: ProgramOptions,
        tag: str | None,
        build_number: int | None,
        output_path: Path | None,
        extra_options: list[str],
        target: str,
        services_path: Path) -> None:
    '''Build a service group for a specific target.

    The SERVICE_GROUP is the path to the folder containing a 'services.yml'
    service group definition file.  The available targets can be listed with
    '--list-targets'.
    '''
    print_header()

    if output_path is None:
        output_path = Path('./build') / f'services.{target}'

    version = _generate_version(tag, build_number)
    service_group = load_service_group(services_path)

    try:
        info = TARGETS[target]
        info.callback(service_group, opts.config, version, output_path, extra_options)
    except KeyError:
        raise CliException(
            f'There is no `{target}` build target.  See available targets with '
            '\'--list-targets\'.'
            )
    except GantryException as e:
        raise CliException(f'Failed to build {services_path}; {str(e)}')
