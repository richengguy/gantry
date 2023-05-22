from urllib.parse import urljoin

from urllib3.exceptions import RequestError
from urllib3.util import Url, parse_url

from .client import AuthType, ForgeAuth, ForgeClient
from .._types import Path
from ..exceptions import ForgeApiOperationFailed
from ..logging import get_app_logger


_logger = get_app_logger('gitea')


class GiteaClient(ForgeClient):
    '''Push service images and definitions to a Gitea repo.'''
    API_BASE_URL = '/api/v1'

    def __init__(self, app_folder: Path, url: str) -> None:
        super().__init__(app_folder, url)
        self._endpoint = urljoin(url, GiteaClient.API_BASE_URL)

    @property
    def endpoint(self) -> Url:
        return parse_url(self._endpoint)

    def get_server_version(self) -> str:
        try:
            resp = self._http.request('GET', self._version_endpoint, headers=self._headers)
        except RequestError as e:
            _logger.exception('HTTP request failed.', exc_info=e)
            raise ForgeApiOperationFailed(self.provider_name(), 'Initial HTTP request failed.') from e

        if resp.status != 200:
            raise ForgeApiOperationFailed(
                self.provider_name(),
                f'Operation failed with {resp.status}.'
            )
        return resp.json()['version']

    # def _get_new_api_token(self) -> ForgeAuth:
    #     if self._auth_info['auth_type'] != AuthType.BASIC:
    #         raise ForgeApiOperationFailed(
    #             self.provider_name(),
    #             'Gitea token requests require the use of HTTP Basic authentication.'
    #         )

    @staticmethod
    def provider_name() -> str:
        return 'gitea'

    @property
    def _version_endpoint(self) -> str:
        return urljoin(self._endpoint, 'version')
