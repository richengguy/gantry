import click

from ._common import ProgramOptions, print_header
from ..config import Config
from ..exceptions import CliException
from ..logging import get_app_logger


_logger = get_app_logger()


def _check_config(opts: ProgramOptions) -> Config:
    print_header()
    if opts.config is None:
        raise CliException('The \'forge\' commands require a gantry config.')

    _logger.debug('Forge Details')
    _logger.debug('  Provider: %s', opts.config.forge_provider)
    _logger.debug('       URL: %s', opts.config.forge_url)
    _logger.debug('       Org: %s', opts.config.forge_owner)

    return opts.config


@click.group('forge')
@click.pass_obj
def cmd(opts: ProgramOptions) -> None:
    '''Interact with git repos and artifact stores.

    All of the 'forge' subcommands require a gantry configuration file.  The
    configuration file specifies the forge's URL and the account/organization
    it will be working with.
    '''


@cmd.command('auth')
@click.option(
    '--api-token', '-a',
    metavar='API_TOKEN',
    envvar='GANTRY_FORGE_API_TOKEN',
    help=(
        'The API token used to authenticate with the forge.  Gantry is able to '
        'automatically obtain this for some forge providers.  This value can '
        'also be set with the GANTRY_FORGE_API_TOKEN environment variable.'
    ),
    type=str
)
@click.pass_obj
def cmd_authenticate(opts: ProgramOptions, api_token: str | None) -> None:
    '''Authenticate with a software forge.'''
    config = _check_config(opts)

    if api_token is None:
        _logger.debug('API token not provided; will request from \'%s\' provider.',
                      config.forge_provider)
