import json
from pathlib import Path
import stat
from typing import Literal
from urllib.parse import urljoin

import certifi

from gantry import __version__ as gantry_version
from gantry.exceptions import ForgeUrlInvalidError
from gantry.forge import AuthType, ForgeAuth, ForgeClient

import pytest

from urllib3.util import Url, parse_url


class MockForge(ForgeClient):
    def __init__(self, app_folder: Path, *, url: str = "https://localhost") -> None:
        super().__init__(app_folder, url, "mock_account")
        assert self._owner == "mock_account"

    @property
    def api_base_url(self) -> Url:
        return parse_url(urljoin(self._url.url, "/api/v1/mock"))

    def create_repo(self, name: str) -> str:
        return "test/repo"

    def delete_repo(self, name: str) -> str:
        return "test/repo"

    def get_clone_url(self, repo: str, type: Literal["ssh", "https"] = "ssh") -> str:
        return "https://git.example.com"

    def get_server_version(self) -> str:
        return "n/a"

    def list_repos(self) -> list[str]:
        return ["a repo"]

    @staticmethod
    def provider_name() -> str:
        return "mock"


def test_create_new_forge(tmp_path: Path) -> None:
    mock = MockForge(tmp_path)
    auth_file = tmp_path / "mock" / "auth.json"

    assert auth_file.exists()
    assert mock._auth_file == auth_file

    # Directory should have 0700 (only user read/write/execute) permissions.
    info = mock._auth_file.parent.stat()
    mode = (
        info.st_mode & stat.S_IRWXU
        | info.st_mode & stat.S_IRWXG
        | info.st_mode & stat.S_IRWXO
    )
    assert mode == 0o700

    # The auth.json file for a new forge client should be using 'none'
    # authentication with no other information.
    with mock._auth_file.open("rt") as f:
        obj = json.load(f)
        assert obj == ForgeAuth(auth_type=AuthType.NONE)

    # Default headers should be an empty dict.
    assert mock._headers == {"user-agent": f"gantry/{gantry_version}"}

    # Default certs path should be the same as certifi.
    assert mock.ca_certs == certifi.where()


def test_correct_endpoint(tmp_path: Path) -> None:
    mock = MockForge(tmp_path, url="https://example.com")
    assert mock.api_base_url.url == "https://example.com/api/v1/mock"


def test_load_existing_auth_info(tmp_path: Path) -> None:
    auth_file = tmp_path / "mock" / "auth.json"
    auth_file.parent.mkdir(mode=0o700, parents=True)
    with auth_file.open("wt") as f:
        json.dump(ForgeAuth(api_token="123456", auth_type=AuthType.TOKEN), f)

    mock = MockForge(tmp_path)
    assert mock._auth_info["auth_type"] == AuthType.TOKEN
    assert mock._auth_info["api_token"] == "123456"


def test_set_basic_auth(tmp_path: Path) -> None:
    mock = MockForge(tmp_path)
    mock.set_basic_auth(user="abc", passwd="def")

    with mock._auth_file.open("rt") as f:
        info = json.load(f)

    assert info["auth_type"] == AuthType.BASIC
    assert info["username"] == "abc"
    assert info["password"] == "def"


def test_set_token_auth(tmp_path: Path) -> None:
    mock = MockForge(tmp_path)
    mock.set_token_auth(user="test", api_token="123456")

    with mock._auth_file.open("rt") as f:
        info = json.load(f)

    assert info["auth_type"] == AuthType.TOKEN
    assert info["username"] == "test"
    assert info["api_token"] == "123456"


@pytest.mark.parametrize("url", ("localhost", "localhost:999999"))
def test_error_on_invalid_url(url: str, tmp_path: Path) -> None:
    with pytest.raises(ForgeUrlInvalidError):
        MockForge(tmp_path, url=url)

    auth_file = tmp_path / "mock" / "auth.json"
    assert not auth_file.exists()
