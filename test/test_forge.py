import json
from pathlib import Path
import stat

from gantry.exceptions import ForgeUrlInvalidError, ForgeOperationNotSupportedError
from gantry.forge import AuthType, ForgeAuth, ForgeClient

import pytest


class MockForge(ForgeClient):
    def __init__(self,
                 app_folder: Path,
                 *,
                 url: str = 'https://localhost',
                 requests_token: bool = False) -> None:
        self._requests_token = requests_token
        super().__init__(app_folder, url)

    @staticmethod
    def provider_name() -> str:
        return 'mock'

    def _get_new_api_token(self) -> ForgeAuth:
        if self._requests_token:
            return ForgeAuth(auth_type=AuthType.TOKEN, api_token='54321')
        else:
            return super()._get_new_api_token()


def test_create_new_forge(tmp_path: Path) -> None:
    mock = MockForge(tmp_path)
    auth_file = tmp_path / 'mock' / 'auth.json'

    assert auth_file.exists()
    assert mock._auth_file == auth_file

    # Directory should have 0700 (only user read/write/execute) permissions.
    info = mock._auth_file.parent.stat()
    mode = (
        info.st_mode & stat.S_IRWXU |
        info.st_mode & stat.S_IRWXG |
        info.st_mode & stat.S_IRWXO
    )
    assert mode == 0o700

    # The auth.json file for a new forge client should be 'basic' with no other
    # information.
    with mock._auth_file.open('rt') as f:
        obj = json.load(f)
        assert obj == ForgeAuth(auth_type=AuthType.BASIC)


def test_load_existing_auth_info(tmp_path: Path) -> None:
    auth_file = tmp_path / 'mock' / 'auth.json'
    auth_file.parent.mkdir(mode=0o700, parents=True)
    with auth_file.open('wt') as f:
        json.dump(ForgeAuth(api_token='123456', auth_type=AuthType.TOKEN), f)

    mock = MockForge(tmp_path)
    assert mock._auth_info['auth_type'] == AuthType.TOKEN
    assert mock._auth_info['api_token'] == '123456'


def test_set_basic_auth(tmp_path: Path) -> None:
    mock = MockForge(tmp_path)
    mock.set_basic_auth(user='abc', passwd='def')

    with mock._auth_file.open('rt') as f:
        info = json.load(f)

    assert info['auth_type'] == AuthType.BASIC
    assert info['username'] == 'abc'
    assert info['password'] == 'def'


def test_set_token_auth(tmp_path: Path) -> None:
    mock = MockForge(tmp_path)
    mock.set_token_auth(api_token='123456')

    with mock._auth_file.open('rt') as f:
        info = json.load(f)

    assert info['auth_type'] == AuthType.TOKEN
    assert info['api_token'] == '123456'


@pytest.mark.parametrize('url', ('localhost', 'localhost:999999'))
def test_error_on_invalid_url(url: str, tmp_path: Path) -> None:
    with pytest.raises(ForgeUrlInvalidError):
        MockForge(tmp_path, url=url)

    auth_file = tmp_path / 'mock' / 'auth.json'
    assert not auth_file.exists()


def test_error_when_request_api_not_supported(tmp_path: Path) -> None:
    mock = MockForge(tmp_path, requests_token=False)
    with pytest.raises(ForgeOperationNotSupportedError,
                       match='This forge does not support requesting API tokens.'):
        mock.request_api_token()


def test_correct_behavior_when_request_api_supported(tmp_path: Path) -> None:
    mock = MockForge(tmp_path, requests_token=True)
    mock.request_api_token()

    with mock._auth_file.open('rt') as f:
        info = json.load(f)

    assert info['auth_type'] == AuthType.TOKEN
    assert info['api_token'] == '54321'
    assert info == mock._auth_info
