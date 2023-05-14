import logging

import rich.logging

from ._types import PathLike


LOGGER_NAME = 'gantry'


class _ConsoleFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__('%(message)s')

    def format(self, record: logging.LogRecord) -> str:
        output = super().format(record)

        if hasattr(record, 'component') and record.component is not None:
            return f' {record.component} -> {output}'
        else:
            return f' -> {output}'


class _ExceptionsFilter(logging.Filter):
    # Implementation based off of https://stackoverflow.com/a/54605728

    def __init__(self, *, remove: bool) -> None:
        super().__init__(LOGGER_NAME)
        self._remove = remove

    def filter(self, record: logging.LogRecord) -> bool:
        if self._remove:
            record._orig_exc_info = record.exc_info
            record.exc_info = None
            return True

        if hasattr(record, '_orig_exc_info'):
            record.exc_info = record._orig_exc_info
            del record._orig_exc_info

        return True


def init_logger(
        *,
        log_level: int = logging.INFO,
        logfile: PathLike | None = None,
        show_traceback: bool = False
        ) -> None:
    '''Initialize the application logger.

    This should only be called once when the application first starts.

    Parameters
    ----------
    default_level : int
        specify the logging level; defaults to 'info'
    logfile : path-like, optional
        write the logs to a file
    show_traceback : bool
        show exception traceback in the log output
    '''
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # Create the console logging output.
    ch = rich.logging.RichHandler(show_level=True, show_path=False, show_time=False)
    ch.setLevel(log_level)
    ch.addFilter(_ExceptionsFilter(remove=not show_traceback))
    ch.setFormatter(_ConsoleFormatter())

    logger.addHandler(ch)

    # Create the file logger.
    if logfile is not None:
        fh = logging.FileHandler(logfile, 'w')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('{levelname: <8} - {message}', style='{'))
        fh.addFilter(_ExceptionsFilter(remove=False))
        logger.addHandler(fh)


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
    return logging.LoggerAdapter(logger, {'component': component})  # type: ignore
