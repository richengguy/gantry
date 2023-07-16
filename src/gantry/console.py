from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
import logging
from typing import Iterator, TypeVar

from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text


class ActivityDisplay(ABC):
    '''Track the activity of a long-running process.

    An activity display is is something that will display the output from some
    long-running process as well as send it to the application logger.  The
    exact mechanics will depend on the particular implementation.

    The logging output will be prepended with ``<<console>>`` by default.  This
    is to make it easier to parse out the process activity.
    '''
    def __init__(self,
                 logger: logging.Logger,
                 *,
                 process_name: str | None = None,
                 surface: Live | None = None
                 ) -> None:
        '''
        Parameters
        ----------
        logger : :class:`logging.Logger`
            application logger instance
        process_name : str
            user-friendly name of the running process; this should be kept short
            as it gets prepended to the log output
        surface : :class:`rich.live.Live`, optional
            rendering surface; required if the display will be nested within
            another rendering surface otherwise the `rich` library will produce
            an exception
        '''
        self._console_output = Table.grid()
        self._display: 'ProcessDisplay' | None = None
        self._logger = logger
        self._process_name = 'console' if process_name is None else process_name
        self._started = False
        self._surface = Live() if surface is None else surface

    @property
    @abstractmethod
    def task_progress(self) -> Progress:
        '''Progress tracker for the individual task.'''

    @abstractmethod
    def _create_display_group(self, console_output: Table) -> Group:
        '''Create the display shown by this activity.

        Parameters
        ----------
        console_output: :class:`rich.table.Table`
            the element where console output will be written to
        '''

    @property
    def is_started(self) -> bool:
        return self._started

    def start(self) -> 'ProcessDisplay':
        '''Start rendering to the activity display.

        Returns
        -------
        :class:`ProcessDisplay`
            the display context that a process uses to record its output
        '''
        if self._display is not None:
            return self._display

        console_output = Table.grid()
        console_output.add_column()

        self._surface.start(refresh=True)
        self._surface.update(self._create_display_group(console_output), refresh=True)

        self._display = ProcessDisplay(
            self._logger,
            self._process_name,
            self.task_progress,
            console_output
        )

        self._display.start()
        self._started = True
        return self._display

    def stop(self) -> None:
        '''Stop the rendering.'''
        if self._display is not None:
            self._display.stop()
            del self._display
            self._display = None

        self._surface.stop()
        self._started = False

    def __enter__(self) -> 'ProcessDisplay':
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class ConsoleActivityDisplay(ActivityDisplay):
    '''Display the status of a single long-running process on the console.

    The console display consists of two parts: the process output shown in a
    scrolling live display and an indeterminate progress bar, similar to a
    spinner.  The activity display will send the process output to both the
    console as well as the application logger.  The logging output is prepended
    with `<<console>>`.
    '''
    def __init__(self,
                 logger: logging.Logger,
                 *,
                 description: str | None = None,
                 process_name: str | None = None,
                 surface: Live | None = None,
                 ) -> None:
        '''
        Parameters
        ----------
        logger : :class:`logging.Logger`
            application logger instance
        description : str, optional
            if provided, this sets the progress bar's title, otherwise it will
            just use a default string; cannot be used with the 'columns'
            argument
        process_name : str
            user-friendly name of the running process; this should be kept short
            as it gets prepended to the log output
        surface : :class:`rich.live.Live`, optional
            rendering surface; required if the display will be nested within
            another rendering surface otherwise the `rich` library will produce
            an exception
        '''
        super().__init__(logger, process_name=process_name, surface=surface)
        self._task_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Running' if description is None else description),
            BarColumn()
        )

    @property
    def task_progress(self) -> Progress:
        return self._task_progress

    def _create_display_group(self, console_output: Table) -> Group:
        return Group(
            console_output,
            self._task_progress
        )


class MultiActivityDisplay(ActivityDisplay):
    '''Display the status from a sequence of processes.

    This class acts as an iterator over a sequence to show both the individual
    progress along with the overall progress.
    '''
    def __init__(self,
                 stages: Sequence,
                 logger: logging.Logger,
                 *,
                 description: str | None = None,
                 process_name: str | None = None,
                 surface: Live | None = None
                 ) -> None:
        '''
        Parameters
        ----------
        stages : sequence
            the sequence that the output will be generated from
        logger : :class:`logging.Logger`
            application logger instance
        description : str, optional
            if provided, this sets the progress bar's title, otherwise it will
            just use a default string; cannot be used with the 'columns'
            argument
        process_name : str
            user-friendly name of the running process; this should be kept short
            as it gets prepended to the log output
        surface : :class:`rich.live.Live`, optional
            rendering surface; required if the display will be nested within
            another rendering surface otherwise the `rich` library will produce
            an exception
        '''
        super().__init__(logger, process_name=process_name, surface=surface)
        self._stages = stages
        self._task_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Stage'),
            BarColumn()
        )
        self._total_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Running' if description is None else description),
            BarColumn()
        )

    @property
    def task_progress(self) -> Progress:
        return self._task_progress

    def _create_display_group(self, console_output: Table) -> Group:
        return Group(
            self._total_progress,
            console_output,
            self._task_progress,
        )

    def stage_iterator(self) -> Iterator:
        if not self.is_started:
            raise RuntimeError('Activity display must be running to use the iterator.')

        task = self._total_progress.add_task('', start=True, total=len(self._stages))

        for stage in self._stages:
            yield stage
            self._total_progress.update(task, advance=1)

        self._total_progress.update(task, completed=True)


class ProcessDisplay:
    '''The display context for a :class:`ActivityDisplay`.'''
    def __init__(self,
                 logger: logging.Logger,
                 tag: str,
                 progress: Progress,
                 console_output: Table,
                 ) -> None:
        self._console_output = console_output
        self._had_error = False
        self._logger = logger
        self._progress = progress
        self._started = False
        self._tag = tag
        self._task = TaskID(-1)

    @property
    def is_started(self) -> bool:
        return self._started

    def print_error(self, msg: str) -> None:
        '''Print an error message.

        Parameter
        ---------
        msg : str
            the log message
        '''
        if not self._started:
            return

        text = Text.from_ansi(msg)
        self._logger.error('Error: %s', text.plain.strip())
        self._had_error = True

    def print_output(self, msg: str) -> None:
        '''Print the normal process output.

        Parameter
        ---------
        msg : str
            the log message
        '''
        if not self._started:
            return

        text = Text.from_ansi(msg)
        self._logger.debug('<<%s>> %s', self._tag, text.plain.strip())
        self._console_output.add_row(text)
        self._progress.update(self._task)

    def start(self) -> 'ProcessDisplay':
        '''Start the display context.

        This will cause the display context to become active and accept display
        events.

        Returns
        -------
        :class:`ProcessDisplay`
            the context instance
        '''
        if self._started:
            return self

        self._task = self._progress.add_task('', start=True, total=None)
        self._started = True
        return self

    def stop(self) -> None:
        '''Stops the display context.'''
        if not self._started:
            return

        self._progress.update(self._task, total=1, completed=not self._had_error)
        self._progress.stop_task(self._task)
        self._task = TaskID(-1)
        self._started = False


if __name__ == '__main__':
    import time
    from .logging import get_app_logger
    logger = get_app_logger('test')

    # with ConsoleActivityDisplay(logger, description='Test Process') as reporter:
    #     reporter.print_output('Starting...')
    #     for i in range(10):
    #         reporter.print_output(f'Task {i+1}')
    #         time.sleep(0.3)
    #     reporter.print_error('There was an error!')
    #     reporter.print_output('done!')

    # print('\n\n')

    x = [1, 2, 3]
    multi_activity = MultiActivityDisplay(x, logger)
    with multi_activity as reporter:
        for stage in multi_activity.stage_iterator():
            for i in range(10):
                reporter.print_output(f'Stage {stage}; Task {i + 1}')
                time.sleep(0.3)
