from pathlib import Path
from typing import Callable

from gantry._compose_spec import ComposeFile

from ruamel.yaml import YAML

import pytest

CompileFn = Callable[[str, str], ComposeFile]
ServicesFn = Callable[[str, str], Path]


@pytest.mark.parametrize(
    ('sample', 'expected'),
    [
        ('traefik-default', '/var/run/docker.sock'),
        ('traefik-custom-socket', '/run/users/1001/docker.sock')
    ]
)
def test_router_args(sample: str, expected: str,
                     compile_compose_file: Callable[[str, str], ComposeFile]):
    '''Ensure traefik router args are set correctly.'''
    compose_spec = compile_compose_file('router', sample)
    volumes = compose_spec['services']['proxy']['volumes']
    assert volumes[0] == f'{expected}:/var/run/docker.sock:ro'


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
    assert volumes[1] == './traefik-custom.yml:/traefik.yml:ro'
