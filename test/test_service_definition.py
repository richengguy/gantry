from typing import Callable

from gantry._compose_spec import ComposeFile

import pytest


CompileFn = Callable[[str, str], ComposeFile]


def _get_build_args(compose_spec: ComposeFile, service: str) -> dict[str, str | int]:
    assert 'build' in compose_spec['services'][service]
    return compose_spec['services'][service]['build'].get('args', {})


def _get_routing_rule(compose_spec: ComposeFile, service: str) -> tuple[set[str], int | None]:
    labels = compose_spec['services'][service]['labels']
    path_rule = set(
        rule.strip()
        for rule in labels[f'traefik.http.routers.{service}.rule'].split('||')
    )
    port_rule = labels.get(f'traefik.http.services.{service}.loadbalancer.server.port')
    return (path_rule, port_rule)


@pytest.mark.parametrize(
    ('service', 'expected_rule', 'expected_port'),
    [
        ('complex-entrypoint', {'PathPrefix(`/foo`)', 'PathPrefix(`/bar`)'}, 8080),
        ('default', {'PathPrefix(`/default`)'}, 80),
        ('string-entrypoint', {'PathPrefix(`/my-service`)'}, 80)
    ]
)
def test_entrypoints(service: str, expected_rule: set[str], expected_port: str,
                     compile_compose_file: CompileFn):
    compose_file = compile_compose_file('service-definition', 'entrypoints')
    path_rule, port_rule = _get_routing_rule(compose_file, service)
    assert path_rule == expected_rule
    assert port_rule == expected_port


@pytest.mark.parametrize(
    ('service', 'expected_args'),
    [
        ('no-args', {}),
        ('with-args', {'foo': 1, 'bar': 2})
    ]
)
def test_build_args(service: str, expected_args: dict[str, str | int],
                    compile_compose_file: CompileFn):
    compose_file = compile_compose_file('service-definition', 'build-args')
    build_args = _get_build_args(compose_file, service)
    assert build_args == expected_args
