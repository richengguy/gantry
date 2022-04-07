from abc import ABC, abstractmethod

from ..services import ServiceDefinition


class RoutingProvider(ABC):
    '''Defines the routing provider for the managed services.'''

    @abstractmethod
    def generate_service(self) -> ServiceDefinition:
        '''Generate the service definition for the routing provider.

        Parameters
        ----------
        config : Path
            relative path to the configuration file

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
