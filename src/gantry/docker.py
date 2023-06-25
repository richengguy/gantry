from typing import Literal

import docker
import docker.errors
from docker.constants import DEFAULT_UNIX_SOCKET
# from docker.errors import APIError, DockerException, ImageNotFound
from docker.models.images import Image
from docker.tls import TLSConfig

from ._types import Path
from .exceptions import (
    DockerGenericError,
    DockerConnectionError,
    NoSuchImageError,
    RegistryAuthError
)
from .logging import get_app_logger


_logger = get_app_logger()


class Docker:
    '''Connect to a Docker daemon and interact with it.

    This wraps around the high-level :class:`docker.DockerClient` from the
    Docker Python API to make streamline some common operations.  The original
    client can be accessed with the :attr:`Docker.client` property.  When used
    as a context handler it can also send all exceptions to gantry's logging
    system.
    '''

    def __init__(self, *,
                 url: str = DEFAULT_UNIX_SOCKET,
                 ca_certs: str | None = None,
                 config: Path | None = None) -> None:
        '''
        Parameters
        ----------
        url : str
            URL for the client to connect to; defaults to the standard UNIX
            socket
        ca_certs : str, optional
            path to a CA certificate bundle to allow Docker to work with private
            certificate authorities
        config : path, optional
            path to where the docker configuration is stored for credential
            management; uses the Docker API's default if not provided

        Raises
        ------
        :exc:`DockerConnectionError`
            if the client could not be created
        '''
        if ca_certs is None:
            tls = False
        else:
            tls = TLSConfig(ca_cert=ca_certs)

        try:
            _logger.debug('Create Docker client.')
            self._client = docker.DockerClient(base_url=url, tls=tls)
            self._dockercfg = config
        except docker.errors.DockerException as e:
            _logger.critical('Failed to create Docker client.', exc_info=e)
            raise DockerConnectionError() from e

    @property
    def client(self) -> docker.DockerClient:
        ''':class:`docker.DockerClient`: the Docker client instance'''
        return self._client

    def __enter__(self) -> 'Docker':
        return self

    def __exit__(self, type: type | None, exc, tb) -> Literal[False]:
        if type is not None and not issubclass(type, DockerGenericError):
            _logger.exception('Caught an unhandled Docker exception.', exc_info=exc)
        return False

    def get_image(self, name: str) -> Image:
        '''Find a container image with the given name.

        Parameters
        ----------
        client: :class:`docker.DockerClient`
            docker client
        name : str
            image name

        Returns
        -------
        :class:`docker.models.images.Image`
            the image instance

        Raises
        ------
        :exc:`NoSuchImage`
            if the image doesn't exist
        '''
        try:
            return self._client.images.get(name)
        except docker.errors.ImageNotFound as e:
            _logger.error('Cannot find an image called \'%s\'.', name)
            raise NoSuchImageError(name) from e

    def login(self, registry: str, username: str, password: str | None = None) -> None:
        '''Log into a private registry.

        Parameters
        ----------
        registry : str
            registry URL
        username : str
            the user being authenticated; can also be an authentication token
        password : str, optional
            the password; may be skipped if the user name is an authentication
            token
        '''
        login_args = {
            'registry': registry,
            'username': username
        }

        if password is not None:
            login_args['password'] = password

        if self._dockercfg is not None:
            login_args['dockercfg_path'] = self._dockercfg.as_posix()

        try:
            result = self._client.login(**login_args)
        except docker.errors.APIError as e:
            _logger.error('Could not log in: %s', result['message'], exc_info=e)
            raise RegistryAuthError(registry)

    @staticmethod
    def create_low_level_api(*, url: str = DEFAULT_UNIX_SOCKET) -> docker.APIClient:
        '''Create the Docker low-level API client.

        This will create an instance of :class:`docker.APIClient` that
        provides access to the low-level API.  All error handling and logging
        must be handled directly.

        See the `docker.py docs <https://docker-py.readthedocs.io>`_ for
        details.

        Parameters
        ----------
        url : str
            URL for the client to connect to; defaults to the standard UNIX
            socket

        Returns
        -------
        :class:`docker.APIClient`
            an instance of the low-level API client

        Raises
        ------
        :exc:`DockerConnectionError`
            if the client could not be created
        '''
        try:
            _logger.debug('Create low-level Docker API client.')
            return docker.APIClient(base_url=url)
        except docker.errors.DockerException as e:
            _logger.critical('Failed to create Docker API client.', exc_info=e)
            raise DockerConnectionError() from e
