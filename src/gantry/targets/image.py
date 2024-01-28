from typing import Iterator

from ._common import (
    CopyServiceResources,
    CreateBuildFolder,
    Pipeline,
    Target,
    MANIFEST_FILE,
)

from .._types import Path, PathLike
from ..build_manifest import BuildManifest, Entry, ImageEntry
from ..console import MultiActivityDisplay
from ..docker import Docker
from ..exceptions import ServiceImageBuildError
from ..logging import get_app_logger
from ..services import ServiceDefinition, ServiceGroupDefinition


_logger = get_app_logger("build-image")


def _create_image_name(
    namespace: str | None, tag: str, service: ServiceDefinition
) -> str:
    image_name = f"{service.name}:{tag}"
    if namespace is not None:
        image_name = f"{namespace}/{image_name}"
    return image_name


class BuildDockerImages:
    """Build Docker images for each service in a service group."""

    def __init__(self, build_folder: Path, namespace: str | None, tag: str) -> None:
        self._api = Docker.create_low_level_api()
        self._build_folder = build_folder
        self._namespace = namespace
        self._tag = tag

    def run(self, service_group: ServiceGroupDefinition) -> None:
        def stage_fn(service: ServiceDefinition) -> str:
            image_name = _create_image_name(self._namespace, self._tag, service)
            return f"Image: [bold blue]{image_name}[/bold blue]"

        service_builds = MultiActivityDisplay(
            service_group,
            _logger,
            description="Building Services",
            process_name="Docker",
            stage_fn=stage_fn,
        )

        service: ServiceDefinition
        for service, reporter in service_builds:
            # Generate the image name.
            name = service.name  # type: ignore
            dockerfile_folder = (
                (self._build_folder / service_group.name / name).absolute().as_posix()
            )
            image_name = _create_image_name(self._namespace, self._tag, service)

            # Call the Docker API and record its output.
            _logger.debug(
                "Building image '%s' from '%s'", image_name, dockerfile_folder
            )

            response: Iterator[dict[str, str]] = self._api.build(
                path=dockerfile_folder, tag=image_name, rm=True, decode=True
            )

            for item in response:
                if stream := item.get("stream"):
                    reporter.print_output(stream.strip())

                if error := item.get("error"):
                    reporter.print_error(error)
                    raise ServiceImageBuildError()


class GenerateOrUpdateManifestFile:
    """Generate a manifest file that specifies the versions of each service."""

    def __init__(
        self, manifest_name: str, build_folder: Path, namespace: str | None, tag: str
    ) -> None:
        self._build_folder = build_folder
        self._manifest_name = manifest_name
        self._namespace = namespace
        self._tag = tag

    def run(self, service_group: ServiceGroupDefinition) -> None:
        entries: list[Entry] = [
            ImageEntry(
                _create_image_name(self._namespace, self._tag, service),
                Path(service_group.name) / service.name / "Dockerfile",
            )
            for service in service_group
        ]

        manifest_json = self._build_folder / MANIFEST_FILE

        try:
            manifest = BuildManifest.load(manifest_json)
            for entry in entries:
                manifest.append_entry(entry)
            manifest.save(manifest_json)
            _logger.debug("Updated manifest at '%s'", manifest_json)
        except FileNotFoundError:
            manifest = BuildManifest(self._manifest_name, entries=entries)
            manifest.save(manifest_json)
            _logger.debug("Generated manifest at '%s'", manifest_json)


class ImageTarget(Target):
    """Build the container images for a service group."""

    def __init__(
        self,
        manifest_name: str,
        namespace: str | None,
        tag: str,
        build_folder: PathLike,
        *,
        options: list[str] | None = None,
    ) -> None:
        super().__init__(options=options)
        self._build_folder = Path(build_folder)

        overwrite = "overwrite" in self._parsed_options
        skip_build = "skip-build" in self._parsed_options

        stages: list[Pipeline.Stage] = [
            CreateBuildFolder(
                self._build_folder, overwrite=overwrite, use_group_name=True
            ),
            CopyServiceResources(self._build_folder, use_group_name=True),
            GenerateOrUpdateManifestFile(
                manifest_name, self._build_folder, namespace, tag
            ),
        ]

        if skip_build:
            _logger.info("Docker build stage will be skipped.")
        else:
            stages.append(BuildDockerImages(self._build_folder, namespace, tag))

        self._pipeline = Pipeline(stages=stages)

    def build(self, service_group: ServiceGroupDefinition) -> None:
        _logger.debug("Building images for service group.")
        self._pipeline.run(service_group)

    @staticmethod
    def description() -> str:
        return "Build Docker images for each service in the service group."

    @staticmethod
    def options() -> list[tuple[str, str]]:
        return [
            (
                "overwrite",
                (
                    "Overwrite the contents of the build folder before calling "
                    "`docker build`.  The default behaviour is to prevent "
                    "writing over any existing files in the build directory."
                ),
            ),
            (
                "skip-build",
                (
                    "Skip the actual `docker build` stage.  This will copy all "
                    "of the files needed for the build."
                ),
            ),
        ]
