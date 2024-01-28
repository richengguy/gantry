from typing import NamedTuple

from ._common import (
    CopyServiceResources,
    CreateBuildFolder,
    Pipeline,
    Target,
    MANIFEST_FILE,
)

from .. import routers
from .._compose_spec import ComposeService
from .._types import Path, PathLike
from ..build_manifest import BuildManifest, DockerComposeEntry
from ..exceptions import ComposeServiceBuildError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition
from ..yaml import YamlSerializer


class ConvertedDefinition(NamedTuple):
    name: str
    description: ComposeService


_logger = get_app_logger("compose")


def _convert_to_compose_service(
    service: ServiceDefinition, network: str, tag: str = "custom"
) -> ConvertedDefinition:
    """Convert a service definition into a Compose service dictionary.

    Parameters
    ----------
    service : ServiceDefinition
        some service definition
    network : str
        the network the service should attach to
    tag : str, optional
        the tag to use if the service is being built from a Dockerfile, by
        default 'custom'

    Returns
    -------
    ConvertedDefinition
        the equivalient compose service dictionary
    """
    compose_service: ComposeService = {"container_name": service.name}

    if image := service.image:
        compose_service["image"] = image
    else:
        if folder := service.folder:
            context = folder.relative_to(folder.parent).as_posix()
        else:
            context = "."

        compose_service["image"] = ":".join([service.name, tag])
        compose_service["build"] = {"context": context}

        if build_args := service.build_args:
            compose_service["build"]["args"] = build_args

    compose_service["environment"] = {
        var.key: str(var.value) for var in service.environment
    }
    compose_service["restart"] = "unless-stopped"

    compose_service["ports"] = [str(port) for port in service.service_ports.values()]

    compose_service["networks"] = [network]

    compose_service["volumes"] = []
    compose_service["volumes"].extend(str(f) for f in service.files.values())
    compose_service["volumes"].extend(f"{k}:{v}" for k, v in service.volumes.items())

    if not service.healthcheck:
        compose_service["healthcheck"] = {"disable": True}

    if metadata := service.metadata:
        compose_service["labels"] = metadata

    empty_keys = []
    for key in compose_service:
        if len(compose_service[key]) == 0:  # type: ignore
            empty_keys.append(key)

    for key in empty_keys:
        del compose_service[key]  # type: ignore

    return ConvertedDefinition(service.name, compose_service)


class BuildComposeFile:
    """Pipeline stage to build a Docker Compose file from a service group definition."""

    def __init__(self, build_folder: Path) -> None:
        """
        Parameters
        ----------
        build_folder : path
            path to the top build folder
        """
        self._build_folder = build_folder

    def run(self, service_group: ServiceGroupDefinition) -> None:
        if service_group.router.provider not in routers.PROVIDERS:
            raise ComposeServiceBuildError(
                f"Unknown routing provider `{service_group.router.provider}`."
            )  # noqa: E501

        compose_file = self._build_folder / service_group.name / "docker-compose.yml"

        # The extra '_config-file' property is used to inject the configuration
        # file to the router.
        router_args = service_group.router.args.copy()
        router_args["config-file"] = service_group.router.config.path.name
        router = routers.PROVIDERS[service_group.router.provider](router_args)

        services = map(
            router.register_service, [router.generate_service()] + list(service_group)
        )

        service_mapping: dict[str, ComposeService] = {}
        volumes: set[str] = set()
        for service in services:
            compose_service = _convert_to_compose_service(
                service, service_group.network
            )
            service_mapping[compose_service.name] = compose_service.description

            for volume in service.volumes.keys():
                volumes.add(volume)

        compose_spec = {
            "services": service_mapping,
            "networks": {service_group.network: None},
            "volumes": {volume: None for volume in volumes},
        }

        yaml = YamlSerializer()
        yaml.to_file(compose_spec, compose_file)

        _logger.debug("Built compose file to '%s'", compose_file)


class BuildRouterConfig:
    """Pipeline stage to build a router configuration file."""

    def __init__(self, output: Path) -> None:
        self._output = output

    def run(self, service_group: ServiceGroupDefinition) -> None:
        router = service_group.router
        context = {
            "service": {"name": service_group.name, "network": service_group.network}
        }

        config_file = self._output / service_group.name / router.config.path.name
        with config_file.open("wt") as f:
            f.write(router.config.render(context))

        _logger.debug("Built router config to '%s'", config_file)


class GenerateOrUpdateManifestFile:
    def __init__(self, manifest_name: str, build_folder: Path) -> None:
        self._build_folder = build_folder
        self._manifest_name = manifest_name

    def run(self, service_group: ServiceGroupDefinition) -> None:
        compose_file = self._build_folder / service_group.name / "docker-compose.yml"
        manifest_json = self._build_folder / MANIFEST_FILE

        entry = DockerComposeEntry(compose_file.relative_to(self._build_folder), True)

        try:
            manifest = BuildManifest.load(manifest_json)
            manifest.append_entry(entry)
            manifest.save(manifest_json)
            _logger.debug("Updated manifest at '%s'", manifest_json)
        except FileNotFoundError:
            manifest = BuildManifest(self._manifest_name, entries=[entry])
            manifest.save(manifest_json)
            _logger.debug("Generated manifest at '%s'", manifest_json)


class ComposeTarget(Target):
    """Convert a service group into a Docker Compose file."""

    def __init__(
        self, manifest_name: str, output: PathLike, *, options: list[str] | None = None
    ) -> None:
        super().__init__(options=options)
        self._output = Path(output)

        overwrite = "overwrite" in self._parsed_options

        self._pipeline = Pipeline(
            stages=[
                CreateBuildFolder(
                    self._output, overwrite=overwrite, use_group_name=True
                ),
                BuildComposeFile(self._output),
                BuildRouterConfig(self._output),
                CopyServiceResources(self._output, use_group_name=True),
                GenerateOrUpdateManifestFile(manifest_name, self._output),
            ]
        )

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug("Converting service group to Docker Compose configuration.")
        self._pipeline.run(service_group)

    @staticmethod
    def description() -> str:
        return "Convert a service group into a Docker Compose configuration."

    @staticmethod
    def options() -> list[tuple[str, str]]:
        return [
            (
                "overwrite",
                (
                    "Overwrite an existing Docker Composer configuration "
                    "located at the build folder.  The default behaviour is to "
                    "avoid writing over any existing files in the build "
                    "directory."
                ),
            )
        ]
