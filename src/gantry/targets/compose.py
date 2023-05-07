from ._common import Target, copy_services_resources
from .._types import Path, PathLike
from ..exceptions import ComposeServiceBuildError
from ..services import ServiceGroupDefinition
from ..yaml import YamlSerializer


class ComposeTarget(Target):
    '''Convert a service group into a Docker Compose file.'''
    def __init__(self, output: PathLike, overwrite: bool = False) -> None:
        super().__init__()
        self._output = Path(output)
        self._overwrite = overwrite

        if self._output.exists() and not self._overwrite:
            raise ComposeServiceBuildError(f'Cannot build services; {output} already exists.')

    def build(self, service_group: ServiceGroupDefinition) -> None:
        yaml = YamlSerializer()

        self._output.mkdir(parents=False, exist_ok=self._overwrite)

        compose_spec = _build_compose_file(service_group)
        _build_router_config(service_group, output)
        copy_services_resources(service_group, self._output)

        yaml.to_file(compose_spec, self._output / 'docker-compose.yml')
