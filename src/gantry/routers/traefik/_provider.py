import importlib.resources
from io import StringIO
from pathlib import Path
import shutil

from jinja2 import Environment

from ruamel.yaml import YAML

from ._config import TraefikConfig
from .. import RoutingProvider
from ...exceptions import ServiceManagerException
from ...services import ServiceDefinition


DOCKER_SOCKET = '/var/run/docker.sock'
SERVICE_FILE = 'proxy-service.yml'


def _get_service_file() -> str:
    resource = importlib.resources.files(__package__).joinpath(SERVICE_FILE)
    with importlib.resources.as_file(resource) as path:
        with path.open() as f:
            return f.read()


def _get_dynamic_config(args: dict) -> Path | None:
    value: str | None = args.get('dynamic-config')
    if value is None:
        return None
    else:
        return Path(value)


class TraefikRoutingProvider(RoutingProvider):
    '''Configures Traefik as the services' routing provider.'''

    def __init__(self, args: dict) -> None:
        super().__init__(args)

    def copy_resources(self, services_folder: Path, output_folder: Path):
        dynamic_config = _get_dynamic_config(self.args)
        if dynamic_config is None:
            return

        resource_path = services_folder / dynamic_config
        if not resource_path.is_dir():
            raise ServiceManagerException(f'`{dynamic_config}` is not a folder.')

        output_path = output_folder / resource_path.name
        shutil.copytree(resource_path, output_path)

    def generate_service(self) -> ServiceDefinition:
        template_args = {
            'config_file': self.args['_config-file'],
            'dynamic_config': _get_dynamic_config(self.args),
            'enable_tls': self.args.get('enable-tls', False),
            'map_socket': self.args.get('map-socket', True),
            'socket_path': self.args.get('socket', DOCKER_SOCKET),
        }

        env = Environment()
        output = env.from_string(_get_service_file()).render(**template_args)

        yaml = YAML()
        with StringIO(output) as s:
            return ServiceDefinition(definition=yaml.load(s))

    def register_service(self, service: ServiceDefinition) -> ServiceDefinition:
        entrypoint = service.entrypoint

        config = TraefikConfig()
        config.set_enable_tls(self.args.get('enable-tls', False))
        config.set_port(entrypoint.listens_on)
        for url in entrypoint.routes:
            config.add_route(url)

        for key, value in config.to_labels(service.name).items():
            service.set_metadata(key, value)

        return service
