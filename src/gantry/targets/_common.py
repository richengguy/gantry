from abc import ABC, abstractmethod
from typing import Protocol
import shutil

from .. import routers
from .._types import Path
from ..exceptions import GantryException
from ..logging import get_app_logger
from ..services import ServiceGroupDefinition


_logger = get_app_logger('generic-target')


class Pipeline:
    '''A pipeline for processing service groups.'''

    class Stage(Protocol):
        '''Protocol for any class that can act as a pipeline stage.'''

        def run(self, service_group: ServiceGroupDefinition) -> None:
            '''Run the pipeline stage on a service group.

            Parameters
            ----------
            service_group : :class:`ServiceGroupDefinition`
                service group
            '''

    def __init__(self, *, stages: list['Pipeline.Stage'] = []) -> None:
        '''
        Parameters
        ----------
        stages : list of :class:`Pipeline.Stage`
            the initial set of stages in the pipeline, defaults to an empty list
        '''
        self._stages: list['Pipeline.Stage'] = []
        self._stages.extend(stages)

    @property
    def num_stages(self) -> int:
        '''int: The number of stages in the pipeline.'''
        return len(self._stages)

    def add_stage(self, stage: 'Pipeline.Stage') -> None:
        '''Add a stage to the end of the pipeline.

        Parameters
        ----------
        stage : :class:`Pipeline.Stage`
            a pipeline stage
        '''
        self._stages.append(stage)

    def run(self, service_group: ServiceGroupDefinition) -> None:
        '''Run the pipeline on a service group.

        Parameters
        ----------
        service_group : :class:`ServiceGroupDefinition`
            the service group to process with the pipeline
        '''
        for stage in self._stages:
            stage.run(service_group)


class Target(ABC):
    '''Defines a build target for a service group.'''

    def __init__(self, *, options: list[str] | None = None) -> None:
        super().__init__()
        self._parsed_options: dict[str, str] = {}

        if options is None:
            return

        accepted_options = [name for name, _ in self.options()]
        for opt in options:
            parts = opt.split('=')

            key = ''
            value = ''

            match len(parts):
                case 1:
                    key = parts[0]
                case 2:
                    key = parts[0]
                    value = parts[1]
                case _:
                    raise GantryException('Target option must be a string or a "key=value" fromat.')

            if key not in accepted_options:
                raise GantryException(f'Target does not support a "{key}" option.')

            self._parsed_options[key] = value

    @abstractmethod
    def build(self, service_group: ServiceGroupDefinition) -> None:
        '''Build the service group.'''

    @staticmethod
    @abstractmethod
    def description() -> str:
        '''Provide a short description about the target.'''

    @staticmethod
    @abstractmethod
    def options() -> list[tuple[str, str]]:
        '''Returns a list of options that the target can accept.'''


class CopyServiceResources:
    '''Pipeline stage to copy the service resource folders.

    This wraps :func:`copy_service_resources` to allow it to be used as a stage
    in a build pipeline.
    '''
    def __init__(self, folder: Path, *, use_group_name: bool = False) -> None:
        self._folder = folder
        self._use_group_name = use_group_name

    def run(self, service_group: ServiceGroupDefinition) -> None:
        if self._use_group_name:
            folder = self._folder / service_group.name
        else:
            folder = self._folder

        _logger.debug('Copying service resources to \'%s\'.', folder)
        copy_services_resources(service_group, folder)


class CreateBuildFolder:
    def __init__(
        self, build_folder: Path,
        *,
        overwrite: bool = False,
        use_group_name: bool = False
    ) -> None:
        self._build_folder = build_folder
        self._overwrite = overwrite
        self._use_group_name = use_group_name

    def run(self, service_group: ServiceGroupDefinition) -> None:
        if self._overwrite:
            _logger.debug('Overwriting existing build folder.')

        output = self._build_folder
        if self._use_group_name:
            output /= service_group.name

        output.mkdir(parents=True, exist_ok=self._overwrite)


def copy_services_resources(service_group: ServiceGroupDefinition, folder: Path) -> None:
    '''Copy the service resources into the output folder.

    Parameters
    ----------
    service_group : ServiceGroupDefinition
        service group being generated
    folder : Path
        path to output folder
    '''
    if services_folder := service_group.folder:
        router = routers.PROVIDERS[service_group.router.provider](service_group.router.args)
        router.copy_resources(services_folder, folder)

    for service in service_group:
        if service.folder is None:
            break

        contents = filter(lambda p: p.name != 'service.yml', service.folder.iterdir())

        dst_folder = folder / service.name
        dst_folder.mkdir(exist_ok=True)

        for src in contents:
            dst = dst_folder / src.name
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
