from typing import Callable

from gantry._compose_spec import ComposeFile


def _get_routing_rule(compose_spec: ComposeFile, service: str) -> tuple[str, int | None]:
    labels = compose_spec['services'][service]['labels']
    path_rule = labels[f'traefik.http.routers.{service}.rule']
    port_rule = labels.get(f'traefik.http.services.{service}.loadbalancer.server.port')
    return (path_rule, port_rule)


def test_complex_entrypoint(compile_compose_file: Callable[[str, str], ComposeFile]):
    compose_spec = compile_compose_file('service-definition', 'entrypoints')
    path_rule, port_rule = _get_routing_rule(compose_spec, 'complex-entrypoint')
    assert path_rule == 'PathPrefix(`/foo`) || PathPrefix(`/bar`)'
    assert port_rule == 8080


def test_string_entrypoint(compile_compose_file: Callable[[str, str], ComposeFile]):
    compose_sec = compile_compose_file('service-definition', 'entrypoints')
    path_rule, _ = _get_routing_rule(compose_sec, 'string-entrypoint')
    assert path_rule == 'PathPrefix(`/my-service`)'
