from typing import TypedDict, NotRequired, cast

from ruamel.yaml import YAML

from ._types import PathLike
from .exceptions import ConfigFileValidationError
from .schemas import Schema, validate_object


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


class _ConfigFile(TypedDict):
    gantry: _GantryConfig


class Config:
    """Stores the serialized Gantry configuration."""

    def __init__(self, path: PathLike) -> None:
        """
        Parameters
        ----------
        path : path-like
            the path to the configuration file
        """
        yaml = YAML()
        contents = yaml.load(path)
        errors = validate_object(contents, Schema.CONFIG)

        config = cast(_ConfigFile, contents)["gantry"]

        if len(errors) > 0:
            raise ConfigFileValidationError(errors)

        if "registry" not in config:
            # fmt: off
            config["registry"] = _RegistryConfig(
                url=config["forge"]["url"],
                namespace=config["forge"]["owner"]
            )
            # fmt: on

        self._forge_properties = config["forge"]
        self._registry_properties = config["registry"]

    @property
    def forge_owner(self) -> str:
        """str: Account that gantry interacts with."""
        return self._forge_properties["owner"]

    @property
    def forge_provider(self) -> str:
        """str: The type of forge gantry connects to."""
        return self._forge_properties["provider"]

    @property
    def forge_url(self) -> str:
        """str: The forge URL."""
        return self._forge_properties["url"]

    @property
    def registry_namespace(self) -> str:
        """str: The container namespace when pushing/building containers."""
        return self._registry_properties["namespace"]

    @property
    def registry_url(self) -> str:
        """str: The container registry URL."""
        return self._registry_properties["url"]
