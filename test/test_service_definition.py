from typing import Callable

from gantry._compose_spec import ComposeBuild, ComposeFile

import pytest


CompileFn = Callable[[str, str], ComposeFile]


def _get_build_info(compose_spec: ComposeFile, service: str) -> ComposeBuild:
    assert 'build' in compose_spec['services'][service]
    return compose_spec['services'][service]['build']


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
    assert compose_file['services'][service]['image'] == 'hello-world:latest'
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
    build_info = _get_build_info(compose_file, service)
    assert build_info.get('args', {}) == expected_args
    assert build_info['context'] == service
