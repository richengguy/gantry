import shutil

import docker
from docker.errors import DockerException

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike
from ..exceptions import ClientConnectionError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition


_logger = get_app_logger('build-image')


class _ImageBuilder:
    def __init__(self, folder: Path, registry: str, tag: str) -> None:
        try:
            self._api = docker.from_env()
        except DockerException as e:
            _logger.critical('Failed to create Docker API client.', exc_info=e)
            raise ClientConnectionError from e

        self._folder = folder
        self._registry = registry
        self._tag = tag

    def build(self, service: ServiceDefinition) -> None:
        image_name = f'{self._registry}/{service.name}:{self._tag}'
        _logger.debug('Building image %s', image_name)


class BuildDockerImages:
    '''Build Docker images for each service in a service group.'''
    def __init__(self, build_folder: Path, registry: str, tag: str) -> None:
        self._builder = _ImageBuilder(build_folder, registry, tag)

    def run(self, service_group: ServiceGroupDefinition) -> None:
        for service in service_group:
            self._builder.build(service)


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
            self._build_folder.rmdir()

        self._build_folder.mkdir(parents=False)
        self._pipeline.run(service_group)
