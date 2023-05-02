from typing import TypedDict, NotRequired, cast

from ruamel.yaml import YAML

from ._types import PathLike
from .exceptions import ConfigFileValidationError
from .schemas import Schema, get_schema, validate_object


class _ForgeConfig(TypedDict):
    provider: str
    url: str
    owner: str


class _RegistryConfig(TypedDict):
    url: str
    namespace: str


class _GantryConfig(TypedDict):
    forge: _ForgeConfig
    registry: NotRequired[_RegistryConfig]


class Config:
    '''Stores the serialized Gantry configuration.'''
    def __init__(self, path: PathLike) -> None:
        '''
        Parameters
        ----------
        path : path-like
            the path to the configuration file
        '''
        schema = get_schema(Schema.CONFIG)

        yaml = YAML()
        contents = cast(_GantryConfig, yaml.load(path))
        errors = validate_object(contents, schema)

        if len(errors) > 0:
            raise ConfigFileValidationError(errors)

        if 'registry' not in contents:
            contents['registry'] = _RegistryConfig(
                url=contents['forge']['url'],
                namespace=contents['forge']['owner']
            )

        self._forge_properties = contents['forge']
        self._registry_properties = contents['registry']

    @property
    def forge_owner(self) -> str:
        '''str: Account that gantry interacts with.'''
        return self._forge_properties['owner']

    @property
    def forge_provider(self) -> str:
        '''str: The type of forge gantry connects to.'''
        return self._forge_properties['provider']

    @property
    def forge_url(self) -> str:
        '''str: The forge URL.'''
        return self._forge_properties['url']

    @property
    def registry_namespace(self) -> str:
        '''str: The container namespace when pushing/building containers.'''
        return self._registry_properties['namespace']

    @property
    def registry_url(self) -> str:
        '''str: The container registry URL.'''
        return self._registry_properties['url']
