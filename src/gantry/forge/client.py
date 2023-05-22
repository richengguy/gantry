from abc import ABC, abstractmethod
from enum import StrEnum
import json
from typing import TypedDict, NotRequired

import urllib3
import urllib3.exceptions
import urllib3.util

from .._types import Path
from ..exceptions import (
    CannotObtainForgeAuthError,
    ForgeOperationNotSupportedError,
    ForgeUrlInvalidError
)
from ..logging import get_app_logger


_logger = get_app_logger('forge')


class AuthType(StrEnum):
    '''The authentication types for connecting to a forge.'''
    BASIC = 'basic'
    TOKEN = 'token'


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
            self._url = urllib3.util.parse_url(url)
        except urllib3.exceptions.LocationValueError as e:
            raise ForgeUrlInvalidError(self.provider_name(), url) from e

        if not self._url.scheme == 'https':
            raise ForgeUrlInvalidError(self.provider_name(), url)

        if not provider_folder.exists():
            _logger.debug('Creating \'%s\'.', provider_folder)
            provider_folder.mkdir(mode=0o700, parents=True)

        self._auth_info = self._load_auth_info(self._auth_file)
        self._http = urllib3.PoolManager()

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
        self._store_auth_info(self._auth_file, self._auth_info)

    def set_basic_auth(self, *, user: str, passwd: str) -> None:
        '''Set the client to connect using HTTP basic authentication.

        Parameters
        ----------
        user : str
            username
        passwd : str
            password
        '''
        self._auth_info = ForgeAuth(auth_type=AuthType.BASIC, username=user, password=passwd)
        self._store_auth_info(self._auth_file, self._auth_info)

    def set_token_auth(self, *, api_token: str) -> None:
        '''Set the client to connect using token authentication.

        The exact meaning of "token authentication" will be specific to the
        individual client.

        Parameters
        ----------
        api_token : str
            API tokent
        '''
        self._auth_info = ForgeAuth(auth_type=AuthType.TOKEN, api_token=api_token)
        self._store_auth_info(self._auth_file, self._auth_info)

    @staticmethod
    @abstractmethod
    def provider_name() -> str:
        '''The provider that this client connects to.'''

    def _get_new_api_token(self) -> ForgeAuth:
        '''Obtain a new API token from a forge.

        This should be overridden by a subclass if the operation is supported.
        '''
        raise ForgeOperationNotSupportedError(
            self.provider_name(),
            "This forge does not support requesting API tokens.")

    @classmethod
    def _load_auth_info(cls, auth_file: Path) -> ForgeAuth:
        try:
            with auth_file.open('rt') as f:
                contents = json.load(f)
        except FileNotFoundError:
            contents = ForgeAuth(auth_type=AuthType.BASIC)
            with auth_file.open('wt') as f:
                json.dump(contents, f)
        except PermissionError:
            raise CannotObtainForgeAuthError(cls.provider_name())

        return contents

    @classmethod
    def _store_auth_info(cls, auth_file: Path, auth_info: ForgeAuth) -> None:
        with auth_file.open('wt') as f:
            json.dump(auth_info, f)
