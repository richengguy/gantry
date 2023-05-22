import click

from rich.prompt import Prompt
from rich.console import Console

from ._common import ProgramOptions, print_header
from ..config import Config
from ..exceptions import CliException, ForgeApiOperationFailed
from ..forge import make_client
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
@click.option(
    '--user', '-u', 'username',
    envvar='GANTRY_FORGE_USER',
    help=(
        'The username of the account that gantry will try and connect as.  It '
        'will not be used if \'--api-token\' is set. This value may also be '
        'set using the GANTRY_FORGE_USER environment variable.'
    ),
    type=str
)
@click.option(
    '--pass', '-p', 'password',
    envvar='GANTRY_FORGE_PASS',
    help=(
        'The username of the account that gantry will try and connect as.  It '
        'will not be used if \'--api-token\' is set. This value may also be '
        'set using the GANTRY_FORGE_PASS environment variable.'
    )
)
@click.pass_obj
def cmd_authenticate(opts: ProgramOptions,
                     api_token: str | None,
                     username: str | None,
                     password: str | None) -> None:
    '''Authenticate with a software forge.'''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    if api_token is None:
        _logger.debug('API token not provided; will request from \'%s\' provider.',
                      config.forge_provider)

        if username is None or password is None:
            username = Prompt.ask(' - Username')
            password = Prompt.ask(' - Password', password=True)

        client.set_basic_auth(user=username, passwd=password)
    else:
        pass


@cmd.command('version')
@click.pass_obj
def cmd_version(opts: ProgramOptions) -> None:
    '''Get the version of the remote forge service.

    This gets the version of the remote forge via an API call.  This call may
    fail if gantry has not been already authenticated with the forge.
    '''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    try:
        console = Console()
        with console.status('[blue]Connecting to client...'):
            version = client.get_server_version()
        console.print(f'{client.provider_name()} - {version}')
    except ForgeApiOperationFailed:
        raise CliException('Failed to get version...run with \'gantry -d\' to see traceback.')
