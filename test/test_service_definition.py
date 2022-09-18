from typing import Callable

from gantry._compose_spec import ComposeFile


def test_string_entrypoint(compile_compose_file: Callable[[str, str], ComposeFile]):
    compose_sec = compile_compose_file('service-definition', 'string-entrypoint')
    labels = compose_sec['services']['string-entrypoint']['labels']
    http_rule = labels['traefik.http.routers.string-entrypoint.rule']
    assert http_rule == 'PathPrefix(\'/my-service\')'
