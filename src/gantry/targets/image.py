import json
import shutil
from typing import Generator

import docker
from docker.constants import DEFAULT_UNIX_SOCKET
from docker.errors import DockerException

from rich.progress import Progress, SpinnerColumn, track

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike
from ..exceptions import ClientConnectionError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition


_logger = get_app_logger('build-image')


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

    def build(self, service: ServiceDefinition) -> None:
        image_name = f'{self._registry}/{service.name}:{self._tag}'
        dockerfile_folder = (self._folder / service.name).absolute().as_posix()

        _logger.debug('Building image \'%s\' from \'%s\'', image_name, dockerfile_folder)

        # api_response: Generator[bytes, None, None] = self._api.build(path=dockerfile_folder,
        #                                                              tag=image_name,
        #                                                              rm=True)

        with Progress(SpinnerColumn(), transient=True) as progress:
            progress.add_task(f'Build {service.name}', start=False)
            import time
            for i in range(3):
                time.sleep(1)

            # for output in api_response:
            #     lines = output.splitlines()
            #     for line in lines:
            #         obj: dict[str, str] = json.loads(line)
            #         if text := obj.get('stream'):
            #             progress.log(text.strip(), highlight=False)
            progress.stop()

        # output: bytes
        # for output in self._api.build(path=dockerfile_folder, tag=image_name, rm=True):
        #     parts = output.splitlines()
        #     _console.log(output)
        #     for part in parts:
        #         obj: dict[str, str] = json.loads(part)
        #         if text := obj.get('stream'):
        #             _console.log(text.strip(), highlight=False)


class BuildDockerImages:
    '''Build Docker images for each service in a service group.'''
    def __init__(self, build_folder: Path, registry: str, tag: str) -> None:
        self._builder = _ImageBuilder(build_folder, registry, tag)

    def run(self, service_group: ServiceGroupDefinition) -> None:
        import time
        for service in track(service_group, 'Building...'):
            self._builder.build(service)
            time.sleep(1)


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
