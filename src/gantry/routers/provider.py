from abc import ABC, abstractmethod
from pathlib import Path

from ..services import ServiceDefinition


class RoutingProvider(ABC):
    '''Defines the routing provider for the managed services.'''

    def copy_resources(self, service_folder: Path, output_folder: Path, args: dict):
        '''Copy any resources need by the routing providing.

        The default implementation does nothing.  A provider can override this
        method if it needs to copy files when certain arguments are set.

        Parameters
        ----------
        service_folder : Path
            location of the services group definition folder
        output_folder : Path
            location of the services output folder
        args : dict
            optional arguments that the service can use to configure itself
        '''

    @abstractmethod
    def generate_service(self, args: dict) -> ServiceDefinition:
        '''Generate the service definition for the routing provider.

        Parameters
        ----------
        args : dict
            optional arguments that the service can use to configure itself

        Returns
        -------
        dict
            a dictionary defining the compose service
        '''

    @abstractmethod
    def register_service(self, service: ServiceDefinition) -> ServiceDefinition:
        '''Register a service with the routing provider.

        Registering a service allows the routing provider know where it needs to
        route services.

        Parameters
        ----------
        service : ServiceDefinition
            service being registered

        Returns
        -------
        ServiceDefinition
            the updated service definition
        '''
