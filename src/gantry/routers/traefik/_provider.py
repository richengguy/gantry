import importlib.resources
from io import StringIO

from jinja2 import Environment

from ruamel.yaml import YAML

from ._config import TraefikConfig
from .. import RoutingProvider
from ...services import ServiceDefinition


DOCKER_SOCKET = '/var/run/docker.sock'
SERVICE_FILE = 'proxy-service.yml'


def _get_service_file() -> str:
    with importlib.resources.open_text(__package__, SERVICE_FILE) as f:
        return f.read()


class TraefikRoutingProvider(RoutingProvider):
    '''Configures Traefik as the services' routing provider.'''

    def generate_service(self, args: dict) -> ServiceDefinition:
        template_args = {
            'map_socket': args.get('map-socket', True),
            'socket_path': args.get('socket', DOCKER_SOCKET)
        }

        env = Environment()
        output = env.from_string(_get_service_file()).render(**template_args)

        yaml = YAML()
        with StringIO(output) as s:
            return ServiceDefinition(definition=yaml.load(s))

    def register_service(self, service: ServiceDefinition) -> ServiceDefinition:
        entrypoint = service.entrypoint

        config = TraefikConfig()
        config.set_port(entrypoint.listens_on)
        for url in entrypoint.routes:
            config.add_route(url)

        for key, value in config.to_labels(service.name).items():
            service.set_metadata(key, value)

        return service
