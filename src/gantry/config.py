from typing import TypedDict

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
    registry: _RegistryConfig


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
        contents = yaml.load(path)
        errors = validate_object(contents, schema)

        if len(errors) > 0:
            raise ConfigFileValidationError(errors)
