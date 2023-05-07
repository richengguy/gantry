from abc import ABC, abstractmethod
import shutil

from .. import routers
from .._types import Path
from ..services import ServiceGroupDefinition


class Target(ABC):
    '''Defines a build target for a service group.'''
    @abstractmethod
    def build(self, service_group: ServiceGroupDefinition) -> None:
        '''Build the service group.'''


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
