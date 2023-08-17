import shutil
from typing import Iterator

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike
from ..build_manifest import BuildManifest, ImageEntry
from ..console import MultiActivityDisplay
from ..docker import Docker
from ..exceptions import ServiceImageBuildError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition


_logger = get_app_logger('build-image')


def _create_image_name(namespace: str | None, tag: str, service: ServiceDefinition) -> str:
    image_name = f'{service.name}:{tag}'
    if namespace is not None:
        image_name = f'{namespace}/{image_name}'
    return image_name


class BuildDockerImages:
    '''Build Docker images for each service in a service group.'''
    def __init__(self, build_folder: Path, namespace: str | None, tag: str) -> None:
        self._api = Docker.create_low_level_api()
        self._build_folder = build_folder
        self._namespace = namespace
        self._tag = tag

    def run(self, service_group: ServiceGroupDefinition) -> None:
        def stage_fn(service: ServiceDefinition) -> str:
            image_name = _create_image_name(self._namespace, self._tag, service)
            return f'Image: [bold blue]{image_name}[/bold blue]'

        service_builds = MultiActivityDisplay(
            service_group,
            _logger,
            description='Building Services',
            process_name='Docker',
            stage_fn=stage_fn)

        service: ServiceDefinition
        for service, reporter in service_builds:
            # Generate the image name.
            name = service.name  # type: ignore
            dockerfile_folder = (self._build_folder / name).absolute().as_posix()
            image_name = _create_image_name(self._namespace, self._tag, service)

            # Call the Docker API and record its output.
            _logger.debug('Building image \'%s\' from \'%s\'', image_name, dockerfile_folder)

            response: Iterator[dict[str, str]] = self._api.build(path=dockerfile_folder,
                                                                 tag=image_name,
                                                                 rm=True,
                                                                 decode=True)

            for item in response:
                if stream := item.get('stream'):
                    reporter.print_output(stream.strip())

                if error := item.get('error'):
                    reporter.print_error(error)
                    raise ServiceImageBuildError()


class GenerateManifestFile:
    '''Generate a manifest file that specifies the versions of each service.'''
    def __init__(self, build_folder: Path, namespace: str | None, tag: str) -> None:
        self._build_folder = build_folder
        self._namespace = namespace
        self._tag = tag

    def run(self, service_group: ServiceGroupDefinition) -> None:
        manifest = BuildManifest(entries=[
            ImageEntry(_create_image_name(self._namespace, self._tag, service),
                       Path(service.name) / 'Dockerfile')
            for service in service_group
        ])
        manifest.save(self._build_folder / 'manifest.json')
        _logger.debug('Generated manifest at %s', self._build_folder / 'manifest.json')


class ImageTarget(Target):
    '''Build the container images for a service group.'''
    def __init__(self,
                 namespace: str | None,
                 tag: str,
                 build_folder: PathLike,
                 *,
                 skip_build: bool = False) -> None:
        '''
        Parameters
        ----------
        namespace : str or ``None``
            an optional namespace that is prepended to the image name; optional
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
        stages.append(GenerateManifestFile(self._build_folder, namespace, tag))

        if skip_build:
            _logger.info('Docker build stage will be skipped.')
        else:
            stages.append(BuildDockerImages(self._build_folder, namespace, tag))

        self._pipeline = Pipeline(stages=stages)

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug('Building images for service group.')

        if self._build_folder.exists():
            _logger.debug('Removing existing build directory \'%s\'.', self._build_folder)
            shutil.rmtree(self._build_folder)

        self._build_folder.mkdir(parents=True)
        self._pipeline.run(service_group)
