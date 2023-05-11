import shutil

from ._common import CopyServiceResources, Pipeline, Target

from .._types import Path, PathLike, get_app_logger
from ..services import ServiceGroupDefinition


_logger = get_app_logger('build-image')


class ImageTarget(Target):
    '''Build the container images for a service group.'''
    def __init__(self, output: PathLike) -> None:
        super().__init__()
        self._output = Path(output)

        self._pipeline = Pipeline(stages=[
            CopyServiceResources(self._output)
        ])

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug('Building images for service group.')

        if self._output.exists():
            _logger.debug('Removing existing build directory \'%s\'.', self._output)
            shutil.rmtree(self._output)
            self._output.rmdir()

        self._output.mkdir(parents=False)
        self._pipeline.run(service_group)
