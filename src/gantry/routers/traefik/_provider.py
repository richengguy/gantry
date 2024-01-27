from pathlib import Path
import shutil

from ._config import TraefikConfig
from ...exceptions import ServiceConfigurationException
from ..provider import RoutingProvider, DEFAULT_SERVICE_NAME
from ...services import ServiceDefinition


DOCKER_SOCKET = '/var/run/docker.sock'
TRAEFIK_IMAGE = 'traefik:v2.10.1'
TRAEFIK_CONFIG = '/etc/traefik/traefik.yml'


def _get_dynamic_config(args: dict) -> Path | None:
    value: str | None = args.get('dynamic-config')
    if value is None:
        return None
    else:
        return Path(value)


class TraefikRoutingProvider(RoutingProvider):
    '''Configures Traefik as a service group routing provider.'''

    def __init__(self, args: dict) -> None:
        super().__init__(args)

    def copy_resources(self, services_folder: Path, output_folder: Path):
        dynamic_config = _get_dynamic_config(self.args)
        if dynamic_config is None:
            return

        resource_path = services_folder / dynamic_config
        if not resource_path.is_dir():
            raise ServiceConfigurationException(f'`{dynamic_config}` is not a folder.')

        output_path = output_folder / resource_path.name
        shutil.copytree(resource_path, output_path)

    def generate_service(self) -> ServiceDefinition:
        enable_dashboard = self.args.get('enable-dashboard', False)
        enable_api = enable_dashboard or self.args.get('enable-api', False)

        routes: list[str] = []
        if enable_api:
            routes.append('/api')
        if enable_dashboard:
            routes.append('/dashboard')

        router_definition = {
            'name': DEFAULT_SERVICE_NAME,
            'image': TRAEFIK_IMAGE,
            'internal': not enable_dashboard and not enable_api,
            'entrypoint': {
                'routes': routes
            },
            'files': {
                'static-config': {
                    'internal': TRAEFIK_CONFIG,
                    'external': self.args['config-file']
                }
            },
            'service-ports': {
                'http': {
                    'internal': 80,
                    'external': 80
                }
            },
            'metadata': {}
        }

        if self.args.get('enable-tls', False):
            router_definition['service-ports']['https'] = {  # type: ignore
                'internal': 443,
                'external': 443
            }

        if self.args.get('map-socket', True):
            router_definition['files']['docker-socket'] = {  # type: ignore
                'internal': DOCKER_SOCKET,
                'external': self.args.get('socket', DOCKER_SOCKET)
            }

        if dynamic_config := _get_dynamic_config(self.args):
            router_definition['files']['dynamic-config'] = {  # type: ignore
                'internal': f'/{dynamic_config.name}',
                'external': str(dynamic_config)
            }

        if enable_api or enable_dashboard:
            router_definition['metadata'] = {  # type: ignore
                f'traefik.http.routers.{DEFAULT_SERVICE_NAME}.service': 'api@internal'
            }
        else:
            router_definition['metadata']['traefik.enable'] = True  # type: ignore

        return ServiceDefinition(definition=router_definition)

    def register_service(self, service: ServiceDefinition) -> ServiceDefinition:
        # Internal services are ignored by Traefik when performing automatic
        # labelling.  However, there it's still possible for the necessary
        # labels to be added manually.
        if service.internal:
            return service

        entrypoint = service.entrypoint

        config = TraefikConfig()
        config.set_enable_tls(self.args.get('enable-tls', False))
        config.set_port(entrypoint.listens_on)
        for url in entrypoint.routes:
            config.add_route(url)

        for key, value in config.to_labels(service.name).items():
            service.set_metadata(key, value)

        return service
