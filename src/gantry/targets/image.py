import shutil

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike, get_app_logger
from ..services import ServiceGroupDefinition


_logger = get_app_logger('build-image')


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
        self._registry = registry
        self._tag = tag

        self._pipeline = Pipeline(stages=[
            CopyServiceResources(self._build_folder)
        ])

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug('Building images for service group.')

        if self._build_folder.exists():
            _logger.debug('Removing existing build directory \'%s\'.', self._build_folder)
            shutil.rmtree(self._build_folder)
            self._build_folder.rmdir()

        self._build_folder.mkdir(parents=False)
        self._pipeline.run(service_group)