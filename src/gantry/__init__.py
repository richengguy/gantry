from importlib.metadata import version as _version_info
__version__ = _version_info(__package__)

from .services import ServiceGroupDefinition  # noqa: F401
