from abc import ABC, abstractmethod
from enum import StrEnum
import json
from typing import cast, Any, Callable, Literal, TypedDict, NotRequired

import certifi

from urllib.parse import urljoin

from urllib3 import PoolManager
import urllib3.exceptions
from urllib3.response import BaseHTTPResponse
from urllib3.util import Url, parse_url

from .. import __version__
from .._types import Path
from ..docker import Docker, PushStatus
from ..exceptions import (
    CannotObtainForgeAuthError,
    ForgeApiOperationFailed,
    ForgeOperationNotSupportedError,
    ForgeUrlInvalidError,
)
from ..logging import get_app_logger


_logger = get_app_logger("forge")

HttpMethod = Literal["GET", "DELETE", "PATCH", "POST", "PUT"]


class AuthType(StrEnum):
    """The authentication types for connecting to a forge."""

    BASIC = "basic"
    """Use HTTP Basic authentication."""

    TOKEN = "token"
    """Use a client-specific API token."""

    NONE = "none"
    """Do not use any authentication."""


class ForgeAuth(TypedDict):
    """A dictionary used to store all necessary authentication details."""

    api_token: NotRequired[str]
    auth_type: AuthType
    username: NotRequired[str]
    password: NotRequired[str]


class ForgeClient(ABC):
    """A client to access a software forge.

    The :class:`ForgeClient` allows gantry to perform a set of basic operations
    with a software forge, such as authentication and pushing up container
    images.
    """

    def __init__(self, app_folder: Path, url: str, owner: str) -> None:
        """
        Parameters
        ----------
        app_folder : path
            gantry's working folder
        url : str
            service API URL
        owner : str
            name of the account/organization the client interacts with
        """
        provider_folder = app_folder / self.provider_name()
        self._auth_file = provider_folder / "auth.json"
        self._owner = owner

        try:
            self._url = parse_url(url)
        except urllib3.exceptions.LocationValueError as e:
            raise ForgeUrlInvalidError(self.provider_name(), url) from e

        if not self._url.scheme == "https":
            raise ForgeUrlInvalidError(self.provider_name(), url)

        if not provider_folder.exists():
            _logger.debug("Creating '%s'.", provider_folder)
            provider_folder.mkdir(mode=0o700, parents=True)

        self._load_auth_info()
        self._update_headers()

        self._ca_certs = self._resolve_certs(app_folder)

        self._http = PoolManager(cert_reqs="CERT_REQUIRED", ca_certs=self._ca_certs)

    def authenticate_with_container_registry(self) -> None:
        """Authenticate with the forge's container registry."""
        username: str
        password: str | None
        match self._auth_info["auth_type"]:
            case AuthType.BASIC:
                username = self._auth_info["username"]
                password = self._auth_info["password"]
            case AuthType.TOKEN:
                username = self._auth_info["username"]
                password = self._auth_info["api_token"]
            case AuthType.NONE:
                raise ForgeOperationNotSupportedError(
                    self.provider_name(),
                    "Registry authentication requires forge credentials to "
                    "have been provided.",
                )

        with Docker(ca_certs=self._ca_certs) as client:
            _logger.debug("Logging into container registry at %s", self.url)
            client.login(self.url, username, password)

    @abstractmethod
    def create_repo(self, name: str, desc: str | None = None) -> str:
        """Create a repo on the forge.

        The repo will be created in the organization specified in the gantry
        configuration file.  The repo will be ``<org>/<name>`` on the forge.

        Parameters
        ----------
        name : str
            repo name
        desc : str, optional
            optionally set the repo's description; this will only be applied if
            the forge supports it

        Returns
        -------
        str
            the full name of the newly created repo
        """

    @abstractmethod
    def delete_repo(self, name: str) -> str:
        """Delete a repo on the forge.

        The repo will be deleted in its entirety from the forge.  It is assumed
        to exist in the organization specified in the gantry configuration file.
        This will be ``<org>/<name>`` on the forge.

        Parmaeters
        ----------
        name : str
            repo name

        Returns
        -------
        str
            the full name of the deleted repo
        """

    @abstractmethod
    def get_clone_url(self, repo: str, type: Literal["ssh", "https"] = "ssh") -> str:
        """Get the clone URL for a repo on the software forge.

        This method can return either an SSH or HTTPS clone URL.  By default it
        will return the SSH URL since most clients tend to be configured for
        that.

        Parameters
        ----------
        repo : str
            the repo to request the clone URL for
        type : str
            the type of clone URL to request; can be either ``ssh`` or ``https``

        Returns
        -------
        str
            the clone URL

        Raises
        ------
        :class:`ForgeApiOperationFailed`
            if the repo does not exist
        """

    @abstractmethod
    def get_server_version(self) -> str:
        """Get the version of the forge service the client is connected to.

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
        """

    @abstractmethod
    def list_repos(self) -> list[str]:
        """List the repos associated with the currently authenticated account.

        Returns
        -------
        list of str
            list of repo names
        """

    def push_image(
        self, name: str, *, status_fn: Callable[[PushStatus], None] | None = None
    ) -> None:
        """Push an image to the forge's container registry.

        The client will automatically tag the image (if needed) so it can be
        pushed to the forge's private registry.  For example, if the image name
        is ``image:v1.2`` then a new image name, referencing the original, will
        be created called ``registry.example.com/image:v1.2``.

        Parameters
        ----------
        name : str
            name of the image to push
        status_fn : callable, optional
            accepts a callable object that takes in a :class:`PushStatus`
            object that provides the current state of the push operation
        """
        registry_url = self._url.host
        if registry_url is None:
            raise ForgeUrlInvalidError("Missing the registry URL.", str(self._url))

        should_tag = not name.startswith(registry_url)
        if should_tag:
            full_name = f"{registry_url}/{name}"
        else:
            full_name = name

        with Docker(ca_certs=self._ca_certs) as client:
            if should_tag:
                image = client.get_image(name)
                image.tag(full_name)
                _logger.debug("Tagged image as '%s'.", full_name)

            if status_fn is None:
                client.push_image(full_name)
            else:
                for resp in client.push_image_streaming(full_name):
                    status_fn(resp)

    def send_http_request(
        self,
        method: HttpMethod,
        target: str,
        *,
        body: str | None = None,
        json: Any | None = None,
        success: set[int] = set([200]),
    ) -> BaseHTTPResponse:
        """Send an HTTP request to the forge.

        This is a low-level method used to send requests to a remote forge.  It
        performs some exception handling to ensure that the request went through
        correctly.  If verification passes then the HTTP response object is
        returned.

        The provided endpoint is will be joined with the URL provided when the
        client is first initialized.  The caller will responsible for verifying
        the endpoint, and the request body, are constructed correctly.

        Parameters
        ----------
        method : str
            a string containing the HTTP request type, e.g., 'GET'
        endpoint : str
            the endpoint the request is being sent to
        body : str, optional
            the optional string-encoded HTTP request body
        json : object, optional
            an optional object to encode as a JSON object
        success : set of ints
            the set of expected HTTP status codes indicating a successful
            operation, defaults to ``{200}``

        Returns
        -------
        :class:`BaseHTTPResponse`
            the HTTP response instance

        Raises
        ------
        :exc:`ForgeApiOperationFailed`
            if the HTTP request failed
        """
        endpoint = urljoin(self.api_base_url, target)
        url = urljoin(self._url.url, endpoint)
        try:
            _logger.debug("Making %s request to %s", method, url)
            resp = self._http.request(
                method, url, headers=self._headers, body=body, json=json
            )
        except urllib3.exceptions.RequestError as exc:
            raise ForgeApiOperationFailed(
                self.provider_name(), "Initial HTTP request failed."
            ) from exc

        if resp.status not in success:
            _logger.error("HTTP Status: %d", resp.status)
            _logger.error("Server Response: %s", resp.data.decode("utf-8"))
            raise ForgeApiOperationFailed(
                self.provider_name(), f"Operation failed with {resp.status}."
            )

        return resp

    def set_basic_auth(self, *, user: str, passwd: str) -> None:
        """Set the client to connect using HTTP basic authentication.

        Parameters
        ----------
        user : str
            username
        passwd : str
            password
        """
        _logger.debug(
            "Setting %s to use HTTP Basic authentication.", self.provider_name()
        )
        self._auth_info = ForgeAuth(
            auth_type=AuthType.BASIC, username=user, password=passwd
        )
        self._update_headers()
        self._store_auth_info()

    def set_token_auth(self, *, user: str, api_token: str) -> None:
        """Set the client to connect using token authentication.

        The exact meaning of "token authentication" will be specific to the
        individual client.

        Parameters
        ----------
        user : str
            user the API token is associated with
        api_token : str
            API token
        """
        _logger.debug(
            "Setting %s to use API token authentication.", self.provider_name()
        )
        self._auth_info = ForgeAuth(
            auth_type=AuthType.TOKEN, api_token=api_token, username=user
        )
        self._update_headers()
        self._store_auth_info()

    @property
    def auth_info(self) -> ForgeAuth:
        """:class:`ForgeAuth`: Forge authentication credentials."""
        return self._auth_info

    @property
    def ca_certs(self) -> str:
        """str: Path to the root CA certs used by the forge provider.

        This will always be the path to a single file.  The client will use
        either a custom certificate or one from ``certifi``.  Both cases will
        use certificate bundles.
        """
        return self._ca_certs

    @property
    @abstractmethod
    def api_base_url(self) -> str:
        """str: The base URL for the forge's API."""

    @property
    def owner_account(self) -> str:
        """str: The account the client interacts with."""
        return self._owner

    @property
    def url(self) -> Url:
        """Url: The URL of the software forge."""
        return self._url

    @staticmethod
    @abstractmethod
    def provider_name() -> str:
        """The provider that this client connects to."""

    def _update_headers(self) -> None:
        """Creates the headers that are sent with the API request.

        This will automatically pick the correct authentication type based on
        what was last set on this client.
        """
        user_agent = f"gantry/{__version__}"

        match self._auth_info["auth_type"]:
            case AuthType.BASIC:
                username = self._auth_info.get("username")
                password = self._auth_info.get("password")
                if username is None or password is None:
                    raise ForgeApiOperationFailed(
                        self.provider_name(),
                        "Require username/password with HTTP basic auth.",
                    )
                self._headers = urllib3.util.make_headers(
                    user_agent=user_agent, basic_auth=f"{username}:{password}"
                )
            case AuthType.NONE:
                self._headers = urllib3.util.make_headers(user_agent=user_agent)
            case AuthType.TOKEN:
                api_token = self._auth_info.get("api_token")
                if api_token is None:
                    raise ForgeApiOperationFailed(
                        self.provider_name(), "Request API token with token auth."
                    )
                self._headers = urllib3.util.make_headers(user_agent=user_agent)
                self._headers["Authorization"] = f"token {api_token}"

    def _load_auth_info(self) -> None:
        try:
            with self._auth_file.open("rt") as f:
                self._auth_info = cast(ForgeAuth, json.load(f))
        except FileNotFoundError:
            self._auth_info = ForgeAuth(auth_type=AuthType.NONE)
            with self._auth_file.open("wt") as f:
                json.dump(self._auth_info, f)
        except PermissionError:
            raise CannotObtainForgeAuthError(self.provider_name())

    def _store_auth_info(self) -> None:
        with self._auth_file.open("wt") as f:
            json.dump(self._auth_info, f)

    @classmethod
    def _resolve_certs(cls, app_folder: Path) -> str:
        app_certs = app_folder / "certs" / f"{cls.provider_name()}.ca-bundle"
        if app_certs.exists():
            _logger.debug("Using certs in '%s'.", app_certs)
            return app_certs.absolute().as_posix()
        else:
            return certifi.where()
