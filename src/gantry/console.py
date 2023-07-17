from abc import ABC, abstractmethod
from collections.abc import Callable, Collection, Iterator
import logging
from typing import TypeVar

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

T = TypeVar('T')


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
                 process_name: str | None = None
                 ) -> None:
        '''
        Parameters
        ----------
        logger : :class:`logging.Logger`
            application logger instance
        process_name : str
            user-friendly name of the running process; this should be kept short
            as it gets prepended to the log output
        '''
        self._console_output = Table.grid()
        self._display: 'ProcessDisplay' | None = None
        self._logger = logger
        self._process_name = 'console' if process_name is None else process_name
        self._surface = Live()

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
        return self._display is not None

    def start(self, task_fields: dict = {}) -> 'ProcessDisplay':
        '''Start rendering to the activity display.

        Returns
        -------
        :class:`ProcessDisplay`
            the display context that a process uses to record its output
        '''
        console_output = Table.grid()
        console_output.add_column()

        self._surface.start(refresh=True)
        self._surface.update(self._create_display_group(console_output), refresh=True)

        if self._display is not None:
            return self._display

        self._display = ProcessDisplay(
            self._logger,
            self._process_name,
            self.task_progress,
            console_output,
            task_fields
        )

        self._display.start()
        return self._display

    def stop(self, *, stop_surface: bool = True, clear_surface: bool = True) -> None:
        '''Stop the rendering.

        Parameters
        ----------
        stop_surface : bool
            stop the rendering surface along with display context; default is
            ``True``
        '''
        if self._display is not None:
            self._display.stop()
            del self._display
            self._display = None

        if clear_surface:
            console_output = Table.grid()
            console_output.add_column()
            self._surface.update(self._create_display_group(console_output), refresh=True)

        if stop_surface:
            self._surface.stop()


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
                 process_name: str | None = None
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
        '''
        super().__init__(logger, process_name=process_name)
        self._task_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Running' if description is None else description),
            BarColumn()
        )

    def __enter__(self) -> 'ProcessDisplay':
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    @property
    def task_progress(self) -> Progress:
        return self._task_progress

    def _create_display_group(self, console_output: Table) -> Group:
        return Group(
            self._task_progress,
            console_output,
        )


class MultiActivityDisplay(ActivityDisplay):
    '''Display the status from a sequence of processes.

    This class acts as an iterator over a sequence to show both the individual
    progress along with the overall progress.  The iterator returns a
    ``(stage, reporter)`` tuple.

    For example::

        stages = [1, 2, 3]
        for task, reporter in MultiActivityDisplay(stages, logger):
            report.log_output(f'Processing {task}.')

    The first element is a value from the input sequence while the second is a
    :class:`ProcessDisplay` that allows any output to be recorded by the
    activity display.
    '''
    def __init__(self,
                 stages: Collection[T],
                 logger: logging.Logger,
                 *,
                 description: str | None = None,
                 process_name: str | None = None,
                 stage_fn: Callable[[T], str] | None = None
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
        process_name : str, optional
            user-friendly name of the running process; this should be kept short
            as it gets prepended to the log output
        stage_fn : callable, optional
            an optional callable that takes in a stage value and generates a
            string; if provided, this will set the per-stage descriptions
        '''
        super().__init__(logger, process_name=process_name)
        self._stage_fn = stage_fn
        self._stages = stages
        self._task_progress = Progress(
            TimeElapsedColumn(),
            TextColumn('Stage' if stage_fn is None else '{task.fields[desc]}'),
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
            self._task_progress,
            console_output,
        )

    def __iter__(self) -> Iterator[tuple[T, 'ProcessDisplay']]:
        task = self._total_progress.add_task('', start=True, total=len(self._stages))

        for stage in self._stages:
            if fn := self._stage_fn:
                fields = {'desc': fn(stage)}
            else:
                fields = {}

            yield stage, self.start(fields)
            self._total_progress.update(task, advance=1)
            self.stop(stop_surface=False)

        self.stop(stop_surface=True)


class ProcessDisplay:
    '''The display context for a :class:`ActivityDisplay`.

    The different :class:`ActivityDisplay` classes will provide a
    :class:`ProcessDisplay` for logging.  This should never be created directly
    or stored for later use.
    '''
    def __init__(self,
                 logger: logging.Logger,
                 tag: str,
                 progress: Progress,
                 console_output: Table,
                 task_fields: dict
                 ) -> None:
        self._console_output = console_output
        self._had_error = False
        self._logger = logger
        self._progress = progress
        self._started = False
        self._tag = tag
        self._task = TaskID(-1)
        self._task_fields = task_fields

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

        self._task = self._progress.add_task('', start=True, total=None, **self._task_fields)
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
    # Run this test CLI test using 'python -m gantry.console'

    import time
    from .logging import get_app_logger
    logger = get_app_logger('test')

    with ConsoleActivityDisplay(logger, description='Test Process') as reporter:
        reporter.print_output('Starting...')
        for i in range(10):
            reporter.print_output(f'Task {i+1}')
            time.sleep(0.3)
        reporter.print_error('There was an error!')
        reporter.print_output('done!')

    def stage_fn(stage: int) -> str:
        return f'Stage {stage}'

    print('\n\n')

    x = [1, 2, 3]
    multi_activity_display = MultiActivityDisplay(
        x,
        logger,
        description='Running Multi-stages',
        stage_fn=stage_fn
    )

    stage: int
    for stage, reporter in multi_activity_display:
        for i in range(10):
            reporter.print_output(f'Stage {stage}; Task {i + 1}')
            time.sleep(0.3)

            if stage == 2 and i == 4:
                reporter.print_error(f'Hit an error in stage {stage}!')
