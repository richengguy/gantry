from dataclasses import asdict, dataclass
from typing import cast, Literal, TypedDict

from .client import ForgeClient
from .._types import Path
from ..exceptions import ForgeApiOperationFailed
from ..logging import get_app_logger


_logger = get_app_logger('gitea')


class _Repository(TypedDict):
    id: int
    owner: '_User'
    name: str
    full_name: str
    clone_url: str
    html_url: str
    ssh_url: str


class _User(TypedDict):
    full_name: str
    login: str


@dataclass
class _CreateRepoRequest:
    name: str
    description: str

    auto_init: bool = True
    default_branch: str = 'main'


@dataclass
class _EditRepoRequest:
    has_actions: bool
    has_issues: bool
    has_packages: bool
    has_projects: bool
    has_pull_requests: bool
    has_wiki: bool

    allow_manual_merge: bool = False
    allow_merge_commits: bool = False
    allow_rebase: bool = False
    allow_rebase_update: bool = True
    allow_squash_merge: bool = True
    default_delete_branch_after_merge: bool = True
    default_merge_style: str = 'squash'
    description: str | None = None


class GiteaClient(ForgeClient):
    '''Push service images and definitions to a Gitea repo.'''
    API_BASE_URL = '/api/v1/'

    def __init__(self, app_folder: Path, url: str, owner: str) -> None:
        super().__init__(app_folder, url, owner)

    @property
    def api_base_url(self) -> str:
        return self.API_BASE_URL

    def create_repo(self, name: str, desc: str | None = None) -> str:
        if desc is None:
            desc = 'A gantry-created repo.'

        # Create the repo.
        req_create = _CreateRepoRequest(name, desc)

        resp = self.send_http_request('POST',
                                      self._org_repos_endpoint,
                                      json=asdict(req_create),
                                      success=set([201, 400, 409]))

        match resp.status:
            case 400:
                contents = resp.json()
                _logger.error('URL: %s', contents['url'])
                _logger.error('Message: %s', contents['message'])
                raise ForgeApiOperationFailed(self.provider_name(),
                                              'Request failed; see debug log.')
            case 409:
                raise ForgeApiOperationFailed(
                    self.provider_name(),
                    f'The \'{self.owner_account}/{name}\' repo already exists.')

        repos = cast(_Repository, resp.json())
        _logger.debug('New repository created at %s.', repos['clone_url'])

        # Now perform some basic configuration.
        req_edit = _EditRepoRequest(has_actions=True,
                                    has_issues=False,
                                    has_packages=False,
                                    has_projects=False,
                                    has_pull_requests=True,
                                    has_wiki=False)

        resp = self.send_http_request('PATCH', self._repos_endpoint(name), json=asdict(req_edit))
        repos = cast(_Repository, resp.json())
        _logger.debug('Updated repo properties for %s.', repos['full_name'])
        return repos['full_name']

    def delete_repo(self, name: str) -> str:
        self.send_http_request('DELETE', self._repos_endpoint(name), success=set([204]))
        _logger.debug('Successfully deleted %s/%s.', self.owner_account, name)
        return f'{self.owner_account}/{name}'

    def get_clone_url(self, repo: str, type: Literal['ssh', 'https'] = 'ssh') -> str:
        resp = self.send_http_request('GET', self._repos_endpoint(repo))
        details = cast(_Repository, resp.json())

        match type:
            case 'ssh':
                return details['ssh_url']
            case 'https':
                return details['clone_url']

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
    def _org_repos_endpoint(self) -> str:
        return f'orgs/{self.owner_account}/repos'

    def _repos_endpoint(self, name: str, *, contents: bool = False) -> str:
        url = f'repos/{self.owner_account}/{name}'

        if contents:
            url = f'{url}/contents'

        return url

    @property
    def _version_endpoint(self) -> str:
        return 'version'
