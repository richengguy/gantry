import pygit2  # type: ignore

from rich.progress import Progress, TaskID

from .._types import Path
from ..exceptions import CliException
from ..forge import ForgeClient
from ..logging import get_app_logger


_logger = get_app_logger()


def _configure_pygit2(client: ForgeClient) -> '_GitCallbacks':
    pygit2.settings.set_ssl_cert_locations(client.ca_certs, None)
    return _GitCallbacks(client)


class _GitCallbacks(pygit2.RemoteCallbacks):
    def __init__(self, client: ForgeClient) -> None:
        ssh = Path.home() / '.ssh'
        self._pubkey = ssh / 'id_rsa.pub'
        self._privkey = ssh / 'id_rsa'

        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        super().__init__()

    def set_progress_bar(self, progress: Progress, task: TaskID) -> None:
        self._progress = progress
        self._task_id = task

    def credentials(self, url, username_from_url, allowed_types):
        use_ssh = allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY
        found_pubkey = self._pubkey.exists()
        found_privkey = self._privkey.exists()

        if not use_ssh:
            return None

        if not (found_privkey and found_pubkey):
            return None

        return pygit2.credentials.Keypair(
            username_from_url,
            self._pubkey.as_posix(),
            self._privkey.as_posix(),
            ''
        )

    def transfer_progress(self, stats: pygit2.remote.TransferProgress) -> None:
        if self._progress is None or self._task_id is None:
            return

        self._progress.update(self._task_id,
                              completed=stats.indexed_objects,
                              total=stats.total_objects)


def clone_repo(client: ForgeClient, clone_url: str, dest: Path) -> pygit2.Repository:
    '''Clone a git repo.

    Parameters
    ----------
    client : :class:`ForgeClient`
        forge the repo exists in
    clone_url : str
        the repo's clone URL
    dest : path-like object
        location where the repo is cloned to

    Returns
    -------
    :class:`pygit2.Repository`
        the cloned repo
    '''
    git_callbacks = _configure_pygit2(client)

    try:
        _logger.debug('Cloning from %s to %s.', clone_url, dest)

        with Progress() as progress:
            task = progress.add_task(f':arrow_down_small: Cloning `{clone_url}`')
            git_callbacks.set_progress_bar(progress, task)
            repo = pygit2.clone_repository(clone_url, dest, callbacks=git_callbacks)

        _logger.debug('Finished `git clone`.')
        return repo
    except Exception as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Failed to clone repo...run with \'gantry -d\' to see traceback.')


def discover_repo(candidate_path: Path) -> pygit2.Repository | None:
    '''Look for a repo at a given path.

    Parameters
    ----------
    candidate_path : Path
        a folder that may contain a repo

    Returns
    -------
    :class:`pygit2.Repository` or ``None``
        a repository instance if the folder is a git repo or ``None`` if it
        isn't
    '''
    try:
        return pygit2.Repository(candidate_path.as_posix(), pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH)
    except pygit2.GitError:
        return None
