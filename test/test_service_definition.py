from typing import Callable

from gantry._compose_spec import ComposeFile

import pytest


CompileFn = Callable[[str, str], ComposeFile]


def _get_routing_rule(compose_spec: ComposeFile, service: str) -> tuple[str, int | None]:
    labels = compose_spec['services'][service]['labels']
    path_rule = labels[f'traefik.http.routers.{service}.rule']
    port_rule = labels.get(f'traefik.http.services.{service}.loadbalancer.server.port')
    return (path_rule, port_rule)


@pytest.mark.parametrize(
    ('service', 'expected_rule', 'expected_port'),
    [
        ('complex-entrypoint', 'PathPrefix(`/foo`) || PathPrefix(`/bar`)', 8080),
        ('default', 'PathPrefix(`/default`)', 80),
        ('string-entrypoint', 'PathPrefix(`/my-service`)', 80)
    ]
)
def test_entrypoints(service: str, expected_rule: str, expected_port: str,
                     compile_compose_file: CompileFn):
    compose_file = compile_compose_file('service-definition', 'entrypoints')
    path_rule, port_rule = _get_routing_rule(compose_file, service)
    assert path_rule == expected_rule
    assert port_rule == expected_port
