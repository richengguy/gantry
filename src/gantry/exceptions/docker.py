from ._base import GantryException


class DockerGenericError(GantryException):
    '''Base error for all Docker-related errors.

    These are often, but not always, triggered by lower-level Docker API errors.
    This exception hierarchy is used to convert those Docker errors into
    gantry-specific errors.
    '''
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class DockerConnectionError(DockerGenericError):
    '''Thrown when the program failed to connected to a Docker host.'''
    def __init__(self) -> None:
        super().__init__(
            'There was an error when connecting to a Docker host.  See '
            'Docker-generated exception for details.'
        )


class NoSuchImageError(DockerGenericError):
    '''Thrown when an image cannot be found.'''
    def __init__(self, name: str) -> None:
        super().__init__(f'Cannot find an image called \'{name}\'.')


class RegistryAuthError(DockerGenericError):
    '''Thrown when the Docker SDK cannot log into a private registry.'''
    def __init__(self, registry: str) -> None:
        super().__init__(f'Failed to log into {registry}.')
