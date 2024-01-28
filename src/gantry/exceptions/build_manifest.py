from typing import NamedTuple

from jsonschema.exceptions import ValidationError

from ._base import GantryException


class BuildManifestException(GantryException):
    """Base class for all configuration exceptions."""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class BuildManifestBadFilePathError(BuildManifestException):
    """Raised when a manifest entry is pointing to the wrong item.

    This should generally be caught during file validation but it can also
    happen when generating a manifest.
    """

    def __init__(self, key: str, expected: str, actual: str) -> None:
        self.key = key
        self.expected = expected
        self.actual = actual
        super().__init__(
            f'"The file {key} points to should be {expected}, was {actual}.'
        )


class BuildManifestValidationError(BuildManifestException):
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
            BuildManifestValidationError.ErrorInfo(err.json_path, err.message)
            for err in errors
        ]
        msg = (
            str(errors[0])
            if len(errors) == 1
            else f"Found {len(errors)} errors in build manifest."
        )  # noqa: E501
        super().__init__(msg)

    @property
    def errors(self) -> list[ErrorInfo]:
        """A list of all detected errors."""
        return self._errors
