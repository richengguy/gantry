from typing import Callable

from gantry._compose_spec import ComposeFile

import pytest


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
