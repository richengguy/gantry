from typing import Type

from .client import AuthType, ForgeAuth, ForgeClient
from .gitea import GiteaClient

from ..config import Config as _Config
from .._types import Path as _Path


CLIENTS: dict[str, Type[ForgeClient]] = {
    GiteaClient.provider_name(): GiteaClient
}


def make_client(config: _Config, app_folder: _Path) -> ForgeClient:
    '''Create a new client given the application configuration.

    Parameters
    ----------
    config : :class:`Config`
        the applicatio configuration
    app_folder : path
        application storage folder

    Returns
    -------
    :class:`ForgeClient`
        a new client, based on the provided configuration
    '''
    if client_type := CLIENTS.get(config.forge_provider):
        return client_type(app_folder, config.forge_url)

    raise KeyError(f'Cannot find a \'{config.forge_provider}\' client.')
