import pygit2

from rich.progress import Progress, TaskID

from .._types import Path
from ..exceptions import CliException
from ..forge import AuthType, ForgeClient
from ..logging import get_app_logger


_logger = get_app_logger()


def _configure_pygit2(client: ForgeClient) -> '_GitCallbacks':
    pygit2.settings.set_ssl_cert_locations(client.ca_certs, None)
    return _GitCallbacks(client)


class _GitCallbacks(pygit2.RemoteCallbacks):
    def __init__(self, client: ForgeClient) -> None:
        user = client.auth_info['username']
        match client.auth_info['auth_type']:
            case AuthType.BASIC:
                passwd = client.auth_info['password']
            case AuthType.TOKEN:
                passwd = client.auth_info['api_token']
            case _:
                passwd = ''

        credentials = pygit2.credentials.UserPass(user, passwd)

        self._progress: Progress | None = None
        self._task_id: TaskID | None = None

        super().__init__(credentials=credentials)

    def set_progress_bar(self, progress: Progress, task: TaskID) -> None:
        self._progress = progress
        self._task_id = task

    def transfer_progress(self, stats: pygit2.remote.TransferProgress) -> None:
        if self._progress is None or self._task_id is None:
            return

        self._progress.update(self._task_id,
                              completed=stats.indexed_objects,
                              total=stats.total_objects)


def clone_repo(client: ForgeClient, clone_url: str, dest: Path) -> None:
    '''Clone a git repo.

    Parameters
    ----------
    client : :class:`ForgeClient`
        forge the repo exists in
    clone_url : str
        the repo's clone URL
    dest : path-like object
        location where the repo is cloned to
    '''
    git_callbacks = _configure_pygit2(client)

    try:
        _logger.debug('Cloning from %s to %s.', clone_url, dest)

        with Progress() as progress:
            task = progress.add_task(f':arrow_down_small: Cloning `{clone_url}`')
            git_callbacks.set_progress_bar(progress, task)
            pygit2.clone_repository(clone_url, dest, callbacks=git_callbacks)

        _logger.debug('Finished `git clone`.')
    except Exception as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Failed to clone repo...run with \'gantry -d\' to see traceback.')
