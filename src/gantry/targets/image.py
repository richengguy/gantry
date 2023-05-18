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

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike
from ..exceptions import ClientConnectionError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition


_logger = get_app_logger('build-image')


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
        self._task_id = TaskID(-1)

    def _build_started(self, image: str) -> None:
        self._task_id = self._build_progress.add_task('', image=image, start=True, total=None)

    def _build_complete(self) -> None:
        self._build_progress.update(self._task_id, total=1, completed=True)
        self._build_progress.stop_task(self._task_id)

    def report_start(self, image: str) -> '_ContextWrapper':
        return _BuildStatus._ContextWrapper(image, self)

    def log_output(self, log: str) -> None:
        _logger.debug('<<Docker>> %s', log)
        self._build_output.add_row(log)
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
    def __init__(self, folder: Path, registry: str, tag: str) -> None:
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
        image_name = f'{self._registry}/{service.name}:{self._tag}'
        dockerfile_folder = (self._folder / service.name).absolute().as_posix()

        _logger.debug('Building image \'%s\' from \'%s\'', image_name, dockerfile_folder)

        response: Iterator[bytes] = self._api.build(path=dockerfile_folder, tag=image_name, rm=True)

        # The API reponse is JSON formatted with *multiple* JSON objects being
        # returned in the same newline-terminated string.  The code below is
        # just splitting up the reponse into its individual lines and then
        # logging them if the object contains a 'stream' property.

        with build_status.report_start(image_name) as reporter:
            for segment in response:
                lines = segment.splitlines()
                for line in lines:
                    json_obj: dict[str, str] = json.loads(line)
                    if stream := json_obj.get('stream'):
                        reporter.log_output(stream.strip())


class BuildDockerImages:
    '''Build Docker images for each service in a service group.'''
    def __init__(self, build_folder: Path, registry: str, tag: str) -> None:
        self._builder = _ImageBuilder(build_folder, registry, tag)

    def run(self, service_group: ServiceGroupDefinition) -> None:
        status_reporter = _OverallProcessingStatus(service_group)

        for service in status_reporter.services:
            self._builder.build(service, status_reporter.get_build_status_reporter())


class ImageTarget(Target):
    '''Build the container images for a service group.'''
    def __init__(self, registry: str, tag: str, build_folder: PathLike) -> None:
        '''
        Parameters
        ----------
        registry : str
            name of the registry the images should be pushed to
        tag : str
            the image tag; often this will be the build verison
        build_folder : path-like
            path to the build folder when building the images
        '''
        super().__init__()
        self._build_folder = Path(build_folder)

        self._pipeline = Pipeline(stages=[
            CopyServiceResources(self._build_folder),
            BuildDockerImages(self._build_folder, registry, tag)
        ])

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug('Building images for service group.')

        if self._build_folder.exists():
            _logger.debug('Removing existing build directory \'%s\'.', self._build_folder)
            shutil.rmtree(self._build_folder)

        self._build_folder.mkdir(parents=False)
        self._pipeline.run(service_group)
