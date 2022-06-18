import importlib.resources

from ruamel.yaml import YAML

from ._config import TraefikConfig
from .. import RoutingProvider
from ...services import ServiceDefinition


SERVICE_FILE = 'proxy-service.yml'


class TraefikRoutingProvider(RoutingProvider):
    '''Configures Traefik as the services' routing provider.'''

    def generate_service(self, args: dict) -> ServiceDefinition:
        yaml = YAML()
        with importlib.resources.open_text(__package__, SERVICE_FILE) as f:
            return ServiceDefinition(definition=yaml.load(f))

    def register_service(self, service: ServiceDefinition) -> ServiceDefinition:
        entrypoint = service.entrypoint

        config = TraefikConfig()
        config.set_port(entrypoint.listens_on)
        for url in entrypoint.routes:
            config.add_route(url)

        for key, value in config.to_labels(service.name).items():
            service.set_metadata(key, value)

        return service
