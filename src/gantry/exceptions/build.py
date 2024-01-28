from ._base import GantryException


class BuildError(GantryException):
    """Root exception for all build errors."""


# -- Compose Target Exceptions -- #


class ComposeTargetException(BuildError):
    """Base class for all exceptions when building Compose services."""


class ComposeServiceBuildError(ComposeTargetException):
    """Exception raised when errors occurs building the Compose services."""


# -- Image Target Exceptions -- #


class ImageTargetException(BuildError):
    """Base class for all exceptions when building container images."""


class ClientConnectionError(ImageTargetException):
    """Exception for any errors when connecting to the image build service."""


class ServiceImageBuildError(ImageTargetException):
    """Exception for when the service image failed to build."""
