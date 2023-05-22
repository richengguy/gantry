from abc import ABC, abstractmethod
from enum import StrEnum
import json
from typing import TypedDict, NotRequired

from urllib3 import PoolManager
import urllib3.exceptions
from urllib3.util import Url, parse_url

from .. import __version__
from .._types import Path
from ..exceptions import (
    CannotObtainForgeAuthError,
    ForgeApiOperationFailed,
    ForgeOperationNotSupportedError,
    ForgeUrlInvalidError
)
from ..logging import get_app_logger


_logger = get_app_logger('forge')


class AuthType(StrEnum):
    '''The authentication types for connecting to a forge.'''

    BASIC = 'basic'
    '''Use HTTP Basic authentication.'''

    TOKEN = 'token'
    '''Use a client-specific API token.'''

    NONE = 'none'
    '''Do not use any authentication.'''


class ForgeAuth(TypedDict):
    '''A dictionary used to store all necessary authentication details.'''
    api_token: NotRequired[str]
    auth_type: AuthType
    username: NotRequired[str]
    password: NotRequired[str]


class ForgeClient(ABC):
    '''A client to access a software forge.

    The :class:`ForgeClient` allows gantry to perform a set of basic operations
    with a software forge, such as authentication and pushing up container
    images.  Some clients can also obtain API authentication credentials as part
    of the authentication process.
    '''
    def __init__(self, app_folder: Path, url: str) -> None:
        '''
        Parameters
        ----------
        app_folder : path
            gantry's working folder
        '''
        provider_folder = app_folder / self.provider_name()
        self._auth_file = provider_folder / 'auth.json'

        try:
            self._url = parse_url(url)
        except urllib3.exceptions.LocationValueError as e:
            raise ForgeUrlInvalidError(self.provider_name(), url) from e

        if not self._url.scheme == 'https':
            raise ForgeUrlInvalidError(self.provider_name(), url)

        if not provider_folder.exists():
            _logger.debug('Creating \'%s\'.', provider_folder)
            provider_folder.mkdir(mode=0o700, parents=True)

        self._load_auth_info()
        self._update_headers()

        self._http = PoolManager()

    @abstractmethod
    def get_server_version(self) -> str:
        '''Get the version of the forge service the client is connected to.

        The definition of 'version' will depend on the forge service.  The
        client should know how to interpret the response and return some
        information about the service.

        Returns
        -------
        str
            the returned service version

        Raises
        ------
        :class:`ForgeApiOperationFailed`
            if the client failed to get the server version
        '''

    def request_api_token(self) -> None:
        '''Request an API token from the forge.

        The client must already have some stored authentication credentials,
        e.g. basic auth user name and password, before this call can be made.

        Raises
        ------
        :class:`ForgeAPIOperationFailed`
            when an API operation has failed
        '''
        _logger.debug('Requesting \'%s\' API token from provider at \'%s\'.',
                      self.provider_name(),
                      self._url)
        self._auth_info = self._get_new_api_token()
        self._store_auth_info()

    def set_basic_auth(self, *, user: str, passwd: str) -> None:
        '''Set the client to connect using HTTP basic authentication.

        Parameters
        ----------
        user : str
            username
        passwd : str
            password
        '''
        _logger.debug('Setting %s to use HTTP Basic authentication.', self.provider_name())
        self._auth_info = ForgeAuth(auth_type=AuthType.BASIC, username=user, password=passwd)
        self._update_headers()
        self._store_auth_info()

    def set_token_auth(self, *, api_token: str) -> None:
        '''Set the client to connect using token authentication.

        The exact meaning of "token authentication" will be specific to the
        individual client.

        Parameters
        ----------
        api_token : str
            API tokent
        '''
        _logger.debug('Setting %s to use API token authentication.', self.provider_name())
        self._auth_info = ForgeAuth(auth_type=AuthType.TOKEN, api_token=api_token)
        self._update_headers()
        self._store_auth_info()

    @property
    @abstractmethod
    def endpoint(self) -> Url:
        '''Url: The API endpoint for this client.'''

    @staticmethod
    @abstractmethod
    def provider_name() -> str:
        '''The provider that this client connects to.'''

    def _update_headers(self) -> None:
        '''Creates the headers that are sent with the API request.

        This will automatically pick the correct authentication type based on
        what was last set on this client.
        '''
        user_agent = f'gantry/{__version__}'

        match self._auth_info['auth_type']:
            case AuthType.BASIC:
                username = self._auth_info.get('username')
                password = self._auth_info.get('password')
                if username is None or password is None:
                    raise ForgeApiOperationFailed(
                        self.provider_name(),
                        'Require username/password with HTTP basic auth.'
                    )
                self._headers = urllib3.util.make_headers(
                    user_agent=user_agent,
                    basic_auth=f'{username}:{password}'
                )
            case AuthType.NONE:
                self._headers = urllib3.util.make_headers(user_agent=user_agent)
            case AuthType.TOKEN:
                api_token = self._auth_info.get('api_token')
                if api_token is None:
                    raise ForgeApiOperationFailed(
                        self.provider_name(),
                        'Request API token with token auth.'
                    )
                self._headers = urllib3.util.make_headers(user_agent=user_agent)
                self._headers['Authorization'] = f'token {api_token}'

    def _get_new_api_token(self) -> ForgeAuth:
        '''Obtain a new API token from a forge.

        This should be overridden by a subclass if the operation is supported.
        '''
        raise ForgeOperationNotSupportedError(
            self.provider_name(),
            "This forge does not support requesting API tokens.")

    def _load_auth_info(self) -> None:
        try:
            with self._auth_file.open('rt') as f:
                self._auth_info = json.load(f)
        except FileNotFoundError:
            self._auth_info = ForgeAuth(auth_type=AuthType.NONE)
            with self._auth_file.open('wt') as f:
                json.dump(self._auth_info, f)
        except PermissionError:
            raise CannotObtainForgeAuthError(self.provider_name())

    def _store_auth_info(self) -> None:
        with self._auth_file.open('wt') as f:
            json.dump(self._auth_info, f)
