from pathlib import Path
import shutil
from typing import NamedTuple

from . import routers
from ._compose_spec import ComposeFile, ComposeService
from .exceptions import ComposeServiceBuildError
from .services import ServiceDefinition, ServiceGroupDefinition
from .yaml import YamlSerializer


class ConvertedDefinition(NamedTuple):
    name: str
    description: ComposeService


def build_services(service_group: ServiceGroupDefinition, output: Path, overwrite: bool = False):
    '''Build the services folder given a service group.

    Parameters
    ----------
    service_group : ServiceGroupDefinition
        group of services to be deployed
    output : Path
        folder where the Compose service files will be stored
    overwrite : bool, optional
        overwrite the contents of the output folder, by default 'False' because
        the results will be undefined
    '''
    yaml = YamlSerializer()

    if output.exists() and not overwrite:
        raise ComposeServiceBuildError(f'Cannot build services; {output} already exists.')

    output.mkdir(parents=False, exist_ok=overwrite)

    compose_spec = _build_compose_file(service_group)
    _build_router_config(service_group, output)
    _copy_services_resources(service_group, output)

    yaml.to_file(compose_spec, output / 'docker-compose.yml')


def _build_compose_file(service_group: ServiceGroupDefinition) -> ComposeFile:
    '''Generate a Docker compose/swarm description from a service group.

    Parameters
    ----------
    service_group : ServiceGroupDefinition
        the set of services that will run on a Docker host

    Returns
    -------
    dict
        a dictionary structured as a Docker compose/swarm file that can be
        serialized to YAML or JSON
    '''
    if service_group.router.provider not in routers.PROVIDERS:
        raise ComposeServiceBuildError(f'Unknown routing provider `{service_group.router.provider}`.')  # noqa: E501

    router = routers.PROVIDERS[service_group.router.provider]()
    router_args = service_group.router.args.copy()
    router_args['_config-file'] = service_group.router.config.path.name

    services = map(
        router.register_service,
        [router.generate_service(router_args)] + list(service_group)
    )

    service_mapping: dict[str, ComposeService] = {}
    volumes: set[str] = set()
    for service in services:
        compose_service = _convert_to_compose_service(service, service_group.network)
        service_mapping[compose_service.name] = compose_service.description

        for volume in service.volumes.keys():
            volumes.add(volume)

    return {
        'services': service_mapping,
        'networks': {service_group.network: None},
        'volumes': {volume: None for volume in volumes}
    }


def _build_router_config(service_group: ServiceGroupDefinition, output: Path) -> None:
    '''Build the router configuration file.

    Parameters
    ----------
    service_group : ServiceGroupDefinition
        service group containing the routing information
    output : Path
        output folder
    '''
    router = service_group.router
    context = {
        'service': {
            'name': service_group.name,
            'network': service_group.network
        }
    }

    config_file = output / router.config.path.name
    with config_file.open('wt') as f:
        f.write(router.config.render(context))


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


def _copy_services_resources(service_group: ServiceGroupDefinition, folder: Path) -> None:
    '''Copy the service resources into the output folder.

    Parameters
    ----------
    service_group : ServiceGroupDefinition
        service group being generated
    folder : Path
        path to output folder
    '''
    if services_folder := service_group.folder:
        router = routers.PROVIDERS[service_group.router.provider]()
        router.copy_resources(services_folder, folder, service_group.router.args)

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
