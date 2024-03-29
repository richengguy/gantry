from pathlib import Path
from typing import Callable

from gantry._compose_spec import ComposeFile
from gantry.routers.provider import DEFAULT_SERVICE_NAME

from ruamel.yaml import YAML

import pytest

CompileFn = Callable[[str, str], ComposeFile]
ServicesFn = Callable[[str, str], Path]


def test_router_config_render(compile_services: ServicesFn):
    """Check that the router's configuration is rendered correctly."""
    output_path = compile_services("router", "traefik-custom-config")
    assert (output_path / "traefik-custom.yml").exists()

    # Check that the traefik file sets the network correctly.
    reader = YAML()
    with (output_path / "traefik-custom.yml").open("rt") as f:
        traefik_file = reader.load(f)

    network = traefik_file["providers"]["docker"]["network"]
    assert network == "test"

    # Check that the compose file references the correct traefik file.
    reader = YAML()
    with (output_path / "docker-compose.yml").open("rt") as f:
        compose_spec: ComposeFile = reader.load(f)

    volumes = compose_spec["services"][DEFAULT_SERVICE_NAME]["volumes"]
    expected_volumes = [
        "./traefik-custom.yml:/etc/traefik/traefik.yml:ro",
        "/var/run/docker.sock:/var/run/docker.sock:ro",
    ]
    assert volumes == expected_volumes


def test_router_default_config(compile_services: ServicesFn) -> None:
    """Check that the default configuration is generated correctly."""
    output_path = compile_services("router", "traefik-default")

    reader = YAML()
    with (output_path / "docker-compose.yml").open("rt") as f:
        compose_spec: ComposeFile = reader.load(f)

    # Check that all ports are expected
    ports = compose_spec["services"][DEFAULT_SERVICE_NAME]["ports"]
    expected_ports = ["80:80"]
    assert ports == expected_ports

    # Check that all services are expected
    labels = compose_spec["services"][DEFAULT_SERVICE_NAME]["labels"]
    expected_labels = {"traefik.enable": True}
    assert labels == expected_labels

    # Check that all volumes are expected
    volumes = compose_spec["services"][DEFAULT_SERVICE_NAME]["volumes"]
    expected_volumes = [
        "./traefik.yml:/etc/traefik/traefik.yml:ro",
        "/var/run/docker.sock:/var/run/docker.sock:ro",
    ]
    assert volumes == expected_volumes


def test_router_dynamic_config(compile_services: ServicesFn):
    """Check that Traefik dynamic configuration get sets up correctly."""
    output_path = compile_services("router", "traefik-dynamic-config")

    # Check that the dynamic configuration folder will be mounted as a volume.
    reader = YAML()
    with (output_path / "docker-compose.yml").open("rt") as f:
        compose_spec: ComposeFile = reader.load(f)

    volumes = compose_spec["services"][DEFAULT_SERVICE_NAME]["volumes"]
    assert "./configuration:/configuration:ro" in volumes

    # Check that the configuration folder was copied into the services folder.
    certificates_file = output_path / "configuration" / "certificates.yml"
    assert certificates_file.exists()

    reader = YAML()
    with certificates_file.open("rt") as f:
        certificates = reader.load(f)

    assert certificates["tls"]["certificates"][0]["keyFile"] == "my.key"
    assert certificates["tls"]["certificates"][0]["certFile"] == "my.cert"


def test_router_enable_dashboard(compile_services: CompileFn) -> None:
    """Ensure the Traefik dashboard endpoints are setup correctly when enabled."""
    output_path = compile_services("router", "traefik-enable-dashboard")

    reader = YAML()
    with (output_path / "docker-compose.yml").open("rt") as f:
        compose_spec: ComposeFile = reader.load(f)

    labels = compose_spec["services"][DEFAULT_SERVICE_NAME]["labels"]
    expected_labels = {
        f"traefik.http.routers.{DEFAULT_SERVICE_NAME}.service": "api@internal",
        "traefik.enable": True,
        f"traefik.http.services.{DEFAULT_SERVICE_NAME}.loadbalancer.server.port": 80,
        f"traefik.http.routers.{DEFAULT_SERVICE_NAME}.rule": "PathPrefix(`/api`) || PathPrefix(`/dashboard`)",  # noqa: E501
    }
    assert labels == expected_labels

    ports = compose_spec["services"][DEFAULT_SERVICE_NAME]["ports"]
    expected_ports = ["80:80"]
    assert ports == expected_ports


@pytest.mark.parametrize(
    ("sample", "expected", "has_tls"),
    [
        ("traefik-default", ["80:80"], False),
        ("traefik-enable-tls", ["80:80", "443:443"], True),
    ],
)
def test_router_enable_tls(
    sample: str, expected: list[str], has_tls: bool, compile_compose_file: CompileFn
):
    """Check that TLS is enabled correctly."""
    compose_spec = compile_compose_file("router", sample)

    ports = compose_spec["services"][DEFAULT_SERVICE_NAME]["ports"]
    assert ports == expected

    labels = compose_spec["services"]["service"]["labels"]
    assert labels["traefik.http.services.service.loadbalancer.server.port"] == 80

    # Enabling TLS also adds an extra 'tls' label to each service.
    tls_label = "traefik.http.routers.service.tls"
    if has_tls:
        assert tls_label in labels
        assert labels[tls_label] is True
    else:
        assert tls_label not in labels


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        ("traefik-default", "/var/run/docker.sock"),
        ("traefik-custom-socket", "/run/users/1001/docker.sock"),
    ],
)
def test_router_socket(sample: str, expected: str, compile_compose_file: CompileFn):
    """Ensure traefik router args are set correctly."""
    compose_spec = compile_compose_file("router", sample)
    volumes = compose_spec["services"][DEFAULT_SERVICE_NAME]["volumes"]
    expected_volumes = [
        "./traefik.yml:/etc/traefik/traefik.yml:ro",
        f"{expected}:/var/run/docker.sock:ro",
    ]
    assert volumes == expected_volumes
