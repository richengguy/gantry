from pathlib import Path
from typing import Callable

from gantry._compose_spec import ComposeFile

from ruamel.yaml import YAML

import pytest

CompileFn = Callable[[str, str], ComposeFile]
ServicesFn = Callable[[str, str], Path]


def test_router_config_render(compile_services: ServicesFn):
    '''Check that the router's configuration is rendered correctly.'''
    output_path = compile_services('router', 'traefik-custom-config')
    assert (output_path / 'traefik-custom.yml').exists()

    # Check that the traefik file sets the network correctly.
    reader = YAML()
    with (output_path / 'traefik-custom.yml').open('rt') as f:
        traefik_file = reader.load(f)

    network = traefik_file['providers']['docker']['network']
    assert network == 'test'

    # Check that the compose file references the correct traefik file.
    reader = YAML()
    with (output_path / 'docker-compose.yml').open('rt') as f:
        compose_spec: ComposeFile = reader.load(f)

    volumes = compose_spec['services']['proxy']['volumes']
    assert volumes[1] == './traefik-custom.yml:/etc/traefik/traefik.yml:ro'


def test_router_dynamic_config(compile_services: ServicesFn):
    '''Check that Traefik dynamic configuration get sets up correctly.'''
    output_path = compile_services('router', 'traefik-dynamic-config')

    # Check that the dynamic configuration folder will be mounted as a volume.
    reader = YAML()
    with (output_path / 'docker-compose.yml').open('rt') as f:
        compose_spec: ComposeFile = reader.load(f)

    volumes = compose_spec['services']['proxy']['volumes']
    assert './configuration:/configuration:ro' in volumes

    # Check that the configuration folder was copied into the services folder.
    certificates_file = output_path / 'configuration' / 'certificates.yml'
    assert certificates_file.exists()

    reader = YAML()
    with certificates_file.open('rt') as f:
        certificates = reader.load(f)

    assert certificates['tls']['certificates'][0]['keyFile'] == 'my.key'
    assert certificates['tls']['certificates'][0]['certFile'] == 'my.cert'


@pytest.mark.parametrize(
    ('sample', 'expected', 'has_tls'),
    [
        ('traefik-default', ['80:80'], False),
        ('traefik-enable-tls', ['80:80', '443:443'], True)
    ]
)
def test_router_enable_tls(sample: str, expected: list[str], has_tls: bool,
                           compile_compose_file: CompileFn):
    '''Check that TLS is enabled correctly.'''
    compose_spec = compile_compose_file('router', sample)

    ports = compose_spec['services']['proxy']['ports']
    assert ports == expected

    for service in ['proxy', 'service']:
        labels = compose_spec['services'][service]['labels']
        assert labels[f'traefik.http.services.{service}.loadbalancer.server.port'] == 80

        # Enabling TLS also adds an extra 'tls' label to each service.
        tls_label = f'traefik.http.routers.{service}.tls'
        if has_tls:
            assert tls_label in labels
            assert labels[tls_label] is True
        else:
            assert tls_label not in labels


@pytest.mark.parametrize(
    ('sample', 'expected'),
    [
        ('traefik-default', '/var/run/docker.sock'),
        ('traefik-custom-socket', '/run/users/1001/docker.sock')
    ]
)
def test_router_socket(sample: str, expected: str, compile_compose_file: CompileFn):
    '''Ensure traefik router args are set correctly.'''
    compose_spec = compile_compose_file('router', sample)
    volumes = compose_spec['services']['proxy']['volumes']
    assert volumes[0] == f'{expected}:/var/run/docker.sock:ro'
    assert volumes[1] == './traefik.yml:/etc/traefik/traefik.yml:ro'
