from typing import NamedTuple

from jsonschema.exceptions import ValidationError

from ._base import GantryException


class ConfigException(GantryException):
    """Base class for all configuration exceptions."""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ConfigFileValidationError(ConfigException):
    """Exception raised when a configuration file failed to validate."""

    class ErrorInfo(NamedTuple):
        path: str
        message: str

        def __str__(self) -> str:
            return f"{self.path}: {self.message}"

    def __init__(self, errors: list[ValidationError]) -> None:
        """Initialize a new definition error.

        Parameters
        ----------
        errors : list[ValidationError]
            a list of errors found during schema validation
        """
        self._errors = [
            ConfigFileValidationError.ErrorInfo(err.json_path, err.message)
            for err in errors
        ]
        msg = (
            str(errors[0])
            if len(errors) == 1
            else f"Found {len(errors)} errors in config file."
        )  # noqa: E501
        super().__init__(msg)

    @property
    def errors(self) -> list[ErrorInfo]:
        """A list of all detected errors."""
        return self._errors


class InvalidConfigValueError(ConfigException):
    """Exception raised when a configuration value is invalid.

    This differs from the :exc:`ConfigFileValidationError` in that it represents
    an error parsing a value after it has been loaded from a file.
    """

    def __init__(self, msg: str) -> None:
        super().__init__(msg)
