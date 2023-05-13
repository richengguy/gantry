from pathlib import Path
from typing import NamedTuple

from jsonschema.exceptions import ValidationError

from .._types import PathLike


class ServiceManagerException(Exception):
    '''Base class for all service manager exceptions.'''
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ComposeServiceBuildError(ServiceManagerException):
    '''Exception raised when errors occurs building the Compose services.'''


class InvalidServiceDefinitionError(ServiceManagerException):
    '''Exception raised when a service definition file failed to validate.'''
    class ErrorInfo(NamedTuple):
        path: str
        message: str

        def __str__(self) -> str:
            return f'{self.path}: {self.message}'

    def __init__(self, errors: list[ValidationError]) -> None:
        '''Initialize a new definition error.

        Parameters
        ----------
        errors : list[ValidationError]
            a list of errors found during schema validation
        '''
        self._errors = [
            InvalidServiceDefinitionError.ErrorInfo(err.json_path, err.message)
            for err in errors
        ]
        msg = str(errors[0]) if len(errors) == 1 else f'Found {len(errors)} errors in service definition.'  # noqa: E501
        super().__init__(msg)

    @property
    def errors(self) -> list[ErrorInfo]:
        '''A list of all detected errors.'''
        return self._errors


class MissingTemplateError(ServiceManagerException):
    '''Exception raised when template file is improperly specified.'''
    def __init__(self, path: Path) -> None:
        '''Initialize a new missing template error.

        Parameters
        ----------
        path : Path
            missing template path
        '''
        self._path = path
        super().__init__(f'Cannot find template at `{path}`.')

    @property
    def path(self) -> Path:
        '''Path of the requested, and missing, template.'''
        return self._path


class ServiceDefinitionNotFoundError(ServiceManagerException):
    '''Exception raised when a service definition could not be found.'''

    def __init__(self, folder: PathLike):
        '''Initialize a new "service not found" exception.

        Parameters
        ----------
        folder : PathLike
            path to folder being inspected
        '''
        super().__init__(f'Could not find service definition for `{folder}`')
        self._folder = folder

    @property
    def folder(self) -> PathLike:
        '''Path-like: Folder triggering the error.'''
        return self._folder
