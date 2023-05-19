import json
import shutil
from typing import Iterator

import docker
from docker.constants import DEFAULT_UNIX_SOCKET
from docker.errors import DockerException

from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn
)
from rich.table import Table
from rich.text import Text

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike
from ..exceptions import ClientConnectionError, ServiceImageBuildError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition


_logger = get_app_logger('build-image')


def _create_image_name(registry: str | None, tag: str, service: ServiceDefinition) -> str:
    image_name = f'{service.name}:{tag}'
    if registry is not None:
        image_name = f'{registry}/{image_name}'
    return image_name


class _BuildStatus:
    '''Handle reporting the current build status.'''

    class _ContextWrapper:
        def __init__(self, image: str, build_status: '_BuildStatus') -> None:
            self._build_status = build_status
            self._image = image

        def __enter__(self) -> '_BuildStatus':
            self._build_status._build_started(self._image)
            return self._build_status

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            self._build_status._build_complete()

    def __init__(self, build_progress: Progress, build_output: Table) -> None:
        self._build_output = build_output
        self._build_progress = build_progress
        self._had_error = False
        self._task_id = TaskID(-1)

    def _build_started(self, image: str) -> None:
        self._task_id = self._build_progress.add_task('', image=image, start=True, total=None)

    def _build_complete(self) -> None:
        self._build_progress.update(self._task_id, total=1, completed=not self._had_error)
        self._build_progress.stop_task(self._task_id)

    def report_start(self, image: str) -> '_ContextWrapper':
        return _BuildStatus._ContextWrapper(image, self)

    def log_error(self, error: str) -> None:
        text = Text.from_ansi(error)
        _logger.error('Error: %s', text.plain.strip())
        self._had_error = True

    def log_output(self, log: str) -> None:
        text = Text.from_ansi(log)
        _logger.debug('<<Docker>> %s', text.plain.strip())
        self._build_output.add_row(text)
        self._build_progress.update(self._task_id)


class _OverallProcessingStatus:
    '''Setup the internal renderer to show the overall processing status.'''

    def __init__(self, service_group: ServiceGroupDefinition) -> None:
        self._service_group = service_group

        self._total_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Building Services'),
            BarColumn()
        )

        self._stage_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Image: [bold blue]{task.fields[image]}[/bold blue]'),
            BarColumn()
        )

        self._build_log = _OverallProcessingStatus._create_log()

    def _create_renderable_group(self) -> Group:
        self._build_log = _OverallProcessingStatus._create_log()
        return Group(
            self._total_progress,
            self._stage_progress,
            self._build_log,
        )

    def get_build_status_reporter(self) -> _BuildStatus:
        return _BuildStatus(self._stage_progress, self._build_log)

    @property
    def services(self) -> Iterator[ServiceDefinition]:
        task_id = self._total_progress.add_task('', start=True, total=len(self._service_group))

        with Live() as renderable:
            renderable.update(self._create_renderable_group(), refresh=True)

            for service in self._service_group:
                yield service
                self._total_progress.update(task_id, advance=1)
                renderable.update(self._create_renderable_group(), refresh=True)

        self._total_progress.update(task_id, completed=True)

    @staticmethod
    def _create_log() -> Table:
        table = Table.grid()
        table.add_column()
        return table


class _ImageBuilder:
    def __init__(self, folder: Path, registry: str | None, tag: str) -> None:
        try:
            _logger.debug('Create Docker API client.')
            self._api = docker.APIClient(base_url=DEFAULT_UNIX_SOCKET)
        except DockerException as e:
            _logger.critical('Failed to create Docker API client.', exc_info=e)
            raise ClientConnectionError from e

        self._folder = folder
        self._registry = registry
        self._tag = tag

    def build(self, service: ServiceDefinition, build_status: _BuildStatus) -> None:
        dockerfile_folder = (self._folder / service.name).absolute().as_posix()
        image_name = _create_image_name(self._registry, self._tag, service)

        _logger.debug('Building image \'%s\' from \'%s\'', image_name, dockerfile_folder)

        response: Iterator[dict[str, str]] = self._api.build(path=dockerfile_folder,
                                                             tag=image_name,
                                                             rm=True,
                                                             decode=True)

        # The API contains a 'stream' field that contains the output from the
        # Docker API.  An 'error' field will be present if there was a build
        # error.

        with build_status.report_start(image_name) as reporter:
            for item in response:
                if stream := item.get('stream'):
                    reporter.log_output(stream.strip())

                if error := item.get('error'):
                    reporter.log_error(error)
                    raise ServiceImageBuildError()


class BuildDockerImages:
    '''Build Docker images for each service in a service group.'''
    def __init__(self, build_folder: Path, registry: str | None, tag: str) -> None:
        self._builder = _ImageBuilder(build_folder, registry, tag)

    def run(self, service_group: ServiceGroupDefinition) -> None:
        status_reporter = _OverallProcessingStatus(service_group)

        for service in status_reporter.services:
            self._builder.build(service, status_reporter.get_build_status_reporter())


class GenerateManifestFile:
    '''Generate a manifest file that specifies the versions of each service.'''
    def __init__(self, build_folder: Path, registry: str | None, tag: str) -> None:
        self._build_folder = build_folder
        self._registry = registry
        self._tag = tag

    def run(self, service_group: ServiceGroupDefinition) -> None:
        manifest: list[dict[str, str]] = []
        for service in service_group:
            manifest.append({
                'image': _create_image_name(self._registry, self._tag, service),
                'service': service.name
            })

        manifest_json = self._build_folder / 'manifest.json'
        with manifest_json.open('wt') as f:
            json.dump(manifest, f, indent=2)


class ImageTarget(Target):
    '''Build the container images for a service group.'''
    def __init__(self,
                 registry: str | None,
                 tag: str,
                 build_folder: PathLike,
                 *,
                 skip_build: bool = False) -> None:
        '''
        Parameters
        ----------
        registry : str or ``None``
            name of the registry the images should be pushed to; set to ``None``
            if the image has is not being pushed to a container registry
        tag : str
            the image tag; often this will be the build verison
        build_folder : path-like
            path to the build folder when building the images
        skip_build : bool
            if ``True``, don't perform the Docker build
        '''
        super().__init__()
        self._build_folder = Path(build_folder)

        stages: list[Pipeline.Stage] = []
        stages.append(CopyServiceResources(self._build_folder))
        stages.append(GenerateManifestFile(self._build_folder, registry, tag))

        if skip_build:
            _logger.info('Docker build stage will be skipped.')
        else:
            stages.append(BuildDockerImages(self._build_folder, registry, tag))

        self._pipeline = Pipeline(stages=stages)

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug('Building images for service group.')

        if self._build_folder.exists():
            _logger.debug('Removing existing build directory \'%s\'.', self._build_folder)
            shutil.rmtree(self._build_folder)

        self._build_folder.mkdir(parents=True)
        self._pipeline.run(service_group)
