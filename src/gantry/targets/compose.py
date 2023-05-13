from typing import NamedTuple

from ._common import CopyServiceResources, Pipeline, Target

from .. import routers
from .._compose_spec import ComposeService
from .._types import Path, PathLike
from ..exceptions import ComposeServiceBuildError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition
from ..yaml import YamlSerializer


class ConvertedDefinition(NamedTuple):
    name: str
    description: ComposeService


_logger = get_app_logger('compose')


def _convert_to_compose_service(service: ServiceDefinition,
                                network: str,
                                tag: str = 'custom') -> ConvertedDefinition:
    '''Convert a service definition into a Compose service dictionary.

    Parameters
    ----------
    service : ServiceDefinition
        some service definition
    network : str
        the network the service should attach to
    tag : str, optional
        the tag to use if the service is being built from a Dockerfile, by
        default 'custom'

    Returns
    -------
    ConvertedDefinition
        the equivalient compose service dictionary
    '''
    compose_service: ComposeService = {
        'container_name': service.name
    }

    if image := service.image:
        compose_service['image'] = image
    else:
        if folder := service.folder:
            context = folder.relative_to(folder.parent).as_posix()
        else:
            context = '.'

        compose_service['image'] = ':'.join([service.name, tag])
        compose_service['build'] = {
            'context': context
        }

        if build_args := service.build_args:
            compose_service['build']['args'] = build_args

    compose_service['environment'] = {var.key: str(var.value) for var in service.environment}
    compose_service['restart'] = 'unless-stopped'

    compose_service['ports'] = [str(port) for port in service.service_ports.values()]

    compose_service['networks'] = [network]

    compose_service['volumes'] = []
    compose_service['volumes'].extend(str(f) for f in service.files.values())
    compose_service['volumes'].extend(f'{k}:{v}' for k, v in service.volumes.items())

    if metadata := service.metadata:
        compose_service['labels'] = metadata

    empty_keys = []
    for key in compose_service:
        if len(compose_service[key]) == 0:  # type: ignore
            empty_keys.append(key)

    for key in empty_keys:
        del compose_service[key]  # type: ignore

    return ConvertedDefinition(service.name, compose_service)


class BuildComposeFile:
    '''Pipeline stage to build a Docker Compose file from a service group definition.'''

    def __init__(self, compose_file: Path) -> None:
        '''
        Parameters
        ----------
        compose_file : path
            path to where the compose file should be written to
        '''
        self._output = compose_file

    def run(self, service_group: ServiceGroupDefinition) -> None:
        if service_group.router.provider not in routers.PROVIDERS:
            raise ComposeServiceBuildError(f'Unknown routing provider `{service_group.router.provider}`.')  # noqa: E501

        router_args = service_group.router.args.copy()
        router_args['_config-file'] = service_group.router.config.path.name
        router = routers.PROVIDERS[service_group.router.provider](router_args)

        services = map(
            router.register_service,
            [router.generate_service()] + list(service_group)
        )

        service_mapping: dict[str, ComposeService] = {}
        volumes: set[str] = set()
        for service in services:
            compose_service = _convert_to_compose_service(service, service_group.network)
            service_mapping[compose_service.name] = compose_service.description

            for volume in service.volumes.keys():
                volumes.add(volume)

        compose_spec = {
            'services': service_mapping,
            'networks': {service_group.network: None},
            'volumes': {volume: None for volume in volumes}
        }

        yaml = YamlSerializer()
        yaml.to_file(compose_spec, self._output)

        _logger.debug('Built compose file to \'%s\'', self._output)


class BuildRouterConfig:
    '''Pipeline stage to build a router configuration file.'''
    def __init__(self, output: Path) -> None:
        self._output = output

    def run(self, service_group: ServiceGroupDefinition) -> None:
        router = service_group.router
        context = {
            'service': {
                'name': service_group.name,
                'network': service_group.network
            }
        }

        config_file = self._output / router.config.path.name
        with config_file.open('wt') as f:
            f.write(router.config.render(context))

        _logger.debug('Built router config to \'%s\'', config_file)


class ComposeTarget(Target):
    '''Convert a service group into a Docker Compose file.'''
    def __init__(self, output: PathLike, overwrite: bool = False) -> None:
        super().__init__()
        self._output = Path(output)
        self._overwrite = overwrite

        if self._output.exists() and not self._overwrite:
            raise ComposeServiceBuildError(f'Cannot build services; {output} already exists.')

        self._pipeline = Pipeline(stages=[
            BuildComposeFile(self._output / 'docker-compose.yml'),
            BuildRouterConfig(self._output),
            CopyServiceResources(self._output),
        ])

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug('Converting service group to Docker Compose configuration.')
        if self._overwrite:
            _logger.debug('Overwriting existing Compose configuration.')

        self._output.mkdir(parents=False, exist_ok=self._overwrite)
        self._pipeline.run(service_group)
