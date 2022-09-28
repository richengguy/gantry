from abc import ABC, abstractmethod
from pathlib import Path

from ..services import ServiceDefinition


class RoutingProvider(ABC):
    '''Defines the routing provider for the managed services.'''

    def __init__(self, args: dict) -> None:
        '''Initialize the routing provider using the provided arguments.

        Parameters
        ----------
        args : dict
            optional arguments used for configuring the routing provider
        '''
        self._args = args.copy()

    @property
    def args(self) -> dict:
        '''dict: The routing provider's configuration arguments.'''
        return self._args

    def copy_resources(self, service_folder: Path, output_folder: Path):
        '''Copy any resources need by the routing providing.

        The default implementation does nothing.  A provider can override this
        method if it needs to copy files when certain arguments are set.

        Parameters
        ----------
        service_folder : Path
            location of the services group definition folder
        output_folder : Path
            location of the services output folder
        '''

    @abstractmethod
    def generate_service(self) -> ServiceDefinition:
        '''Generate the service definition for the routing provider.

        Returns
        -------
        ServiceDefinition
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
