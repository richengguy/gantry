from collections.abc import Mapping, MutableMapping
import logging
from pathlib import Path
from typing import Any, NamedTuple

LOGGER_NAME = 'gantry'

PathLike = Path | str


class _ComponentLogger(logging.LoggerAdapter):
    def __init__(self, logger: Any, extra: Mapping[str, object]) -> None:
        super().__init__(logger, extra)

        if 'component' in extra and extra['component'] is not None:
            self._component = f'[{extra["component"]}] '
        else:
            self._component = ''

    def process(self,
                msg: Any,
                kwargs: MutableMapping[str, Any]
                ) -> tuple[Any, MutableMapping[str, Any]]:
        return '%s%s' % (self._component, msg), kwargs


class ProgramOptions(NamedTuple):
    services_path: Path


def get_app_logger(component: str | None = None) -> logging.Logger:
    '''Get an application logger.

    This function ensures that the names of various loggers are used
    consistently throughout the application.  Passing in no component name will
    return the top-level logger.  All configuration should be done using this
    object.  All component-level loggers have names in the format of
    ``gantry.<component>``.

    Parameters
    ----------
    component : str, optional
        component name

    Returns
    -------
    :class:`logging.Logger`
        logger instance
    '''
    name = 'gantry'

    if component is not None:
        name = '.'.join(['gantry', component])

    # The adapter implements the same interface as a logger, and from a user's
    # perspective should be exactly the same.
    logger = logging.getLogger(name)
    return _ComponentLogger(logger, {'component': component})  # type: ignore
