from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar

from jinja2 import Environment, FileSystemLoader

from .exceptions import MissingTemplateError


T = TypeVar("T")


class PortType(Enum):
    """Defines the specific port type."""

    TCP = "tcp"
    UDP = "udp"


class EnvironmentVariable:
    """Specifies the value of an environment variable."""

    def __init__(self, key: str, value: str | int) -> None:
        """Initialize an environment variable representation.

        Parameters
        ----------
        key : str
            the name of the environment variable
        value : str or int
            the environment variable's value
        """
        self._key = key
        self._value = value

    @property
    def key(self) -> str:
        """str: Environment variable name."""
        return self._key

    @property
    def value(self) -> str | int:
        """str: Environment variable value."""
        return self._value

    def format(self) -> str:
        return f"{self._key}={self._value}"


class TemplateReference:
    """Reference to a Jinja2 template file."""

    def __init__(self, folder: Path, filename: Path) -> None:
        """Initialize the template reference.

        Parameters
        ----------
        folder : Path
            folder containing the template reference
        filename : Path
            file name of the template; this is treated as being relative to the
            source file

        Raises
        ------
        MissingTemplateError
            if the template doesn't exist
        """
        self._path = (folder / filename).resolve()
        if not self._path.exists():
            raise MissingTemplateError(self._path)

    @property
    def path(self) -> Path:
        """Path: The path to the template reference file."""
        return self._path

    def render(self, ctx: dict) -> str:
        """Renders the template using the provided context.

        Parameters
        ----------
        ctx : dict
            a dictionary containing the rendering context

        Returns
        -------
        str
            the rendered template
        """
        env = Environment(loader=FileSystemLoader(self._path.parent), autoescape=True)

        template = env.get_template(self._path.name)
        return template.render(ctx)


class ResourceMapping(Generic[T]):
    """Map some resource into a given service."""

    def __init__(self, definition: dict[str, T]) -> None:
        """Initializing a mapping.

        Parameters
        ----------
        definition : dict
            a dictionary containing the mapping
        """
        self._internal = definition["internal"]
        self._external = definition["external"]

    @property
    def internal(self) -> T:
        return self._internal

    @property
    def external(self) -> T:
        return self._external


class PathMapping(ResourceMapping[str]):
    """Maps paths from the host system to a container."""

    def __init__(self, definition: dict[str, str]) -> None:
        super().__init__(definition)
        self._readonly = True
        if "read-only" in definition:
            self._readonly = bool(definition["read-only"])

    @property
    def read_only(self) -> bool:
        """bool: Indicate that the mapping is read-only."""
        return self._readonly

    def __str__(self) -> str:
        msg = f"{self.external}:{self.internal}"
        if self.read_only:
            msg = f"{msg}:ro"
        return msg


class PortMapping(ResourceMapping[int]):
    """Maps a TCP/UDP port from the external network to a container."""

    def __init__(self, definition: dict[str, int]) -> None:
        super().__init__(definition)
        protocol_string = definition.get("protocol", "tcp")
        self._protocol = PortType(protocol_string)

    @property
    def protocol(self) -> PortType:
        """The port's protocol type."""
        return self._protocol

    def __str__(self) -> str:
        msg = f"{self.external}:{self.internal}"
        if self._protocol == PortType.UDP:
            msg = f"{msg}/{PortType.UDP.value}"
        return msg
