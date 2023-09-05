from typing import cast, TypedDict

from .client import ForgeClient
from .._types import Path
from ..exceptions import ForgeApiOperationFailed
from ..logging import get_app_logger


_logger = get_app_logger('gitea')


class _User(TypedDict):
    full_name: str
    login: str


class _Repository(TypedDict):
    id: int
    owner: _User
    name: str
    full_name: str
    clone_url: str
    html_url: str
    ssh_url: str


class GiteaClient(ForgeClient):
    '''Push service images and definitions to a Gitea repo.'''
    API_BASE_URL = '/api/v1/'

    def __init__(self, app_folder: Path, url: str, owner: str) -> None:
        super().__init__(app_folder, url, owner)

    @property
    def api_base_url(self) -> str:
        return self.API_BASE_URL

    def create_repo(self, name: str) -> None:
        ...

    def get_server_version(self) -> str:
        resp = self.send_http_request('GET', self._version_endpoint)
        return resp.json()['version']

    def list_repos(self) -> list[str]:
        repo = self.send_http_request('GET', self._org_repos_endpoint)
        contents = repo.json()

        if not isinstance(contents, list):
            raise ForgeApiOperationFailed(self.provider_name(), 'Expected a list of JSON objects.')

        repos = cast(list[_Repository], contents)
        _logger.debug('Found %d repos in the \'%s\' account.', len(repos), self.owner_account)

        return [repo['name'] for repo in repos]

    @staticmethod
    def provider_name() -> str:
        return 'gitea'

    @property
    def _version_endpoint(self) -> str:
        return 'version'

    @property
    def _org_repos_endpoint(self) -> str:
        return f'orgs/{self.owner_account}/repos'
