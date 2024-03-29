from typing import Callable

from gantry._compose_spec import ComposeBuild, ComposeFile
from gantry._types import Path
from gantry.services import ServiceGroupDefinition

import pytest


CompileFn = Callable[[str, str], ComposeFile]


def _get_build_info(compose_spec: ComposeFile, service: str) -> ComposeBuild:
    assert "build" in compose_spec["services"][service]
    return compose_spec["services"][service]["build"]


def _get_routing_rule(
    compose_spec: ComposeFile, service: str
) -> tuple[set[str], int | None]:
    labels = compose_spec["services"][service]["labels"]
    path_rule = set(
        rule.strip()
        for rule in labels[f"traefik.http.routers.{service}.rule"].split("||")
    )
    port_rule = labels.get(f"traefik.http.services.{service}.loadbalancer.server.port")
    return (path_rule, port_rule)


@pytest.mark.parametrize(
    ("service", "expected_rule", "expected_port"),
    [
        ("complex-entrypoint", {"PathPrefix(`/foo`)", "PathPrefix(`/bar`)"}, 8080),
        ("default", {"PathPrefix(`/default`)"}, 80),
        ("string-entrypoint", {"PathPrefix(`/my-service`)"}, 80),
    ],
)
def test_entrypoints(
    service: str,
    expected_rule: set[str],
    expected_port: str,
    compile_compose_file: CompileFn,
):
    compose_file = compile_compose_file("service-definition", "entrypoints")
    path_rule, port_rule = _get_routing_rule(compose_file, service)
    assert compose_file["services"][service]["image"] == "hello-world:latest"
    assert path_rule == expected_rule
    assert port_rule == expected_port


# fmt: off
@pytest.mark.parametrize(
    ("service", "expected_args"),
    [
        ("no-args", {}),
        ("with-args", {"foo": 1, "bar": 2})
    ]
)
# fmt: on
def test_build_args(
    service: str, expected_args: dict[str, str | int], compile_compose_file: CompileFn
):
    compose_file = compile_compose_file("service-definition", "build-args")
    build_info = _get_build_info(compose_file, service)
    assert build_info.get("args", {}) == expected_args
    assert build_info["context"] == service


def test_collection_interface(samples_folder: Path) -> None:
    service_group = ServiceGroupDefinition(
        samples_folder / "service-definition" / "entrypoints"
    )
    expected = ["complex-entrypoint", "default", "string-entrypoint"]
    assert len(service_group) == 3
    assert list(service.name for service in service_group) == expected
    for service in expected:
        assert service in service_group


def test_disable_healthcheck(compile_compose_file: CompileFn) -> None:
    compose_file = compile_compose_file("service-definition", "healthcheck")
    assert compose_file["services"]["disabled"]["healthcheck"]["disable"] is True
