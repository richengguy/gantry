from abc import ABC
import os.path
from pathlib import Path
from typing import Iterator, NamedTuple

from ruamel.yaml import YAML

from .exceptions import (
    InvalidServiceDefinitionError,
    MissingTemplateError,
    ServiceDefinitionNotFoundError,
    ServiceManagerException
)

from .resources import (
    EnvironmentVariable,
    PathMapping,
    PortMapping,
    TemplateReference
)

from .schemas import Schema, validate_object


def _load_service_definition(folder: Path, ctx: dict) -> dict:
    '''Loads a service definition YAML file.

    The method looks for a 'service.yml' or 'service.yaml' in the provided
    folder.  The '.yml' extension is preferred and will checked first.

    Parameters
    ----------
    folder : Path
        path to the definitions folder
    ctx : dict
        dictionary containing information for rendering a service definition

    Returns
    -------
    dict
        contents of the definition file

    Raises
    ------
    ServiceDefinitionNotFoundError
        if a valid service definition could not be found
    '''
    extensions = ['.yml', '.yaml']
    service_file = Path('service')

    yaml = YAML()

    for extension in extensions:
        try:
            template = TemplateReference(folder, service_file.with_suffix(extension))
            contents = template.render(ctx)
            return yaml.load(contents)
        except MissingTemplateError:
            continue

    raise ServiceDefinitionNotFoundError(folder)


class _ServiceDefinitionBase(ABC):
    '''Base implementation of all service definitions.'''
    def __init__(self, schema: Schema, *,
                 folder: Path | None = None,
                 definition: dict | None = None) -> None:
        '''Initialize the definition base properties.

        The class must be initialized with either a folder containing a
        definition file or a dictionary containing the service definition.

        Parameters
        ----------
        schema : Schema
            schema used for validating/defining this service object
        folder : Path, optional
            path to where the service definition file resides
        definition : dict, optional
            the dictionary containing the service definition

        Raises
        ------
        ValueError
            if the arguments are invalid
        '''
        if folder is not None and definition is not None:
            raise ValueError('Specify only the service folder or definition dictionary.')

        self._folder: Path | None

        if folder:
            ctx = {
                'service': {
                    'folder': os.path.join('.', folder.name)
                }
            }

            self._definition = _load_service_definition(folder, ctx)
            self._folder = folder.resolve()
        elif definition:
            self._definition = definition
            self._folder = None
        else:
            raise ValueError('No service folder or definition dictionary provided.')

        errors = validate_object(self._definition, schema)
        if len(errors) > 0:
            raise InvalidServiceDefinitionError(errors)

    @property
    def folder(self) -> Path | None:
        '''Path to the folder containing the service definition.  Will be ``None`` if loaded from a dictionary.'''   # noqa: E501
        return self._folder

    @property
    def name(self) -> str:
        '''The service's name.'''
        return self._definition['name']


class ServiceDefinition(_ServiceDefinitionBase):
    '''Defines a single containerized service.'''
    class Entrypoint(NamedTuple):
        routes: str
        listens_on: int

    def __init__(self, *, folder: Path | None = None, definition: dict | None = None) -> None:
        super().__init__(Schema.SERVICE, folder=folder, definition=definition)

    @property
    def build_args(self) -> dict[str, str]:
        '''Build arguments that should be passed to Docker when building the service.  Mutually exclusive with :attr:`image`.'''  # noqa: E501
        return self._definition.get('build-args', {})

    @property
    def entrypoint(self) -> Entrypoint:
        '''The externally visible location of the service.'''
        name = f'/{self.name}'
        port = 80

        if 'entrypoint' in self._definition:
            value = self._definition['entrypoint']
            match value:
                case str(value):
                    name = value
                case dict(value):
                    name = value['routes']
                    port = value.get('listens-on', 80)
                case _:
                    raise ValueError('Unknown datatype for service entrypoint.')

        return ServiceDefinition.Entrypoint(name, port)

    @property
    def environment(self) -> list[EnvironmentVariable]:
        '''A list of all environment variables to send to the container.'''
        env_vars: dict[str, str | int] = self._definition.get('environment', {})
        return [EnvironmentVariable(key, value) for key, value in env_vars.items()]

    @property
    def files(self) -> dict[str, PathMapping]:
        '''A mapping of all files that should be mapped to the container.'''
        file_mapping = self._definition.get('files', {})
        return {ref: PathMapping(details) for ref, details in file_mapping.items()}

    @property
    def image(self) -> str | None:
        '''The name of the container image.  Mutually exclusive with :attr:`build_args`.'''
        return self._definition.get('image')

    @property
    def metadata(self) -> dict[str, str | int | bool] | None:
        '''A dictionary containing optional metadata.'''
        return self._definition.get('metadata')

    @property
    def service_ports(self) -> dict[str, PortMapping]:
        '''A mapping of all ports that should be exposed by the service.'''
        port_mapping = self._definition.get('service-ports', {})
        return {ref: PortMapping(details) for ref, details in port_mapping.items()}

    @property
    def volumes(self) -> dict[str, str]:
        '''A mapping of all volumes requested by the service.'''
        vols: dict[str, str] = self._definition.get('volumes', {})
        return {f'{self.name}-{vol_name}': path for vol_name, path in vols.items()}

    def set_metadata(self, key: str, value: str | int | bool, override: bool = False) -> None:
        '''Set some metadata on the service description.

        The default behaviour is to only append metadata and not modify any
        existing metadata.

        Parameters
        ----------
        key : str
            key being set
        value : str | int | bool
            value to set
        override : bool, optional
            allow an existing metadata key to be overridden, by default False

        Raises
        ------
        ValueError
            if ``override`` is ``False`` and ``key`` already exists
        '''
        if 'metadata' not in self._definition:
            self._definition['metadata'] = {}

        if key in self._definition and not override:
            raise ValueError(f'`{key}` is already specified in the definition\'s metadata.')

        self._definition['metadata'][key] = value


class ServiceGroupDefinition(_ServiceDefinitionBase):
    '''Define a group of services that run on a Docker host.

    Services in the service group can be accessed either using both the
    :attr:`services` property or by iterating directly over the group.
    '''
    class RouterInfo(NamedTuple):
        provider: str
        config: TemplateReference
        args: dict

    def __init__(self, folder: Path) -> None:
        super().__init__(Schema.SERVICE_GROUP, folder=folder)

    @property
    def network(self) -> str:
        '''Name of the network that the services communicate on.'''
        return self._definition['network']

    @property
    def router(self) -> RouterInfo:
        '''The service provider used to route messages between services.'''
        if self.folder is None:
            raise ServiceManagerException('Group definition not loaded from a folder.')

        router = self._definition['router']
        config = TemplateReference(self.folder, router['config'])
        args = router.get('args', {})
        return ServiceGroupDefinition.RouterInfo(router['provider'], config, args)

    @property
    def services(self) -> dict[str, ServiceDefinition]:
        '''All of the services within the service group.'''
        return {
            name: ServiceDefinition(folder=self.folder / name)
            for name in self._definition['services']
        }

    def __iter__(self) -> Iterator[ServiceDefinition]:
        if self.folder is None:
            return

        name: str
        for name in self._definition['services']:
            yield ServiceDefinition(folder=self.folder / name)
