from abc import ABC, abstractmethod
from enum import StrEnum
import json
from typing import TypedDict, NotRequired

import certifi

from urllib3 import PoolManager
import urllib3.exceptions
from urllib3.util import Url, parse_url

from .. import __version__
from .._types import Path
from ..exceptions import (
    CannotObtainForgeAuthError,
    ForgeApiOperationFailed,
    ForgeUrlInvalidError,
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
    images.
    '''
    def __init__(self, app_folder: Path, url: str) -> None:
        '''
        Parameters
        ----------
        app_folder : path
            gantry's working folder
        url : str
            service API URL
        cert : path, optional
            path to a custom root cert if the forge does not use a public cert
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

        self._ca_certs = self._resolve_certs(app_folder)

        self._http = PoolManager(
            cert_reqs='CERT_REQUIRED',
            ca_certs=self._ca_certs
        )

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
    def ca_certs(self) -> str:
        '''str: Path to the root CA certs used by the forge provider.'''
        return self._ca_certs

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

    @classmethod
    def _resolve_certs(cls, app_folder: Path) -> str:
        app_certs = app_folder / 'certs' / f'{cls.provider_name()}.ca-bundle'
        if app_certs.exists():
            _logger.debug('Using certs in \'%s\'.', app_certs)
            return app_certs.absolute().as_posix()
        else:
            return certifi.where()
