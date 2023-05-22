import click

from rich.prompt import Prompt
from rich.console import Console

from ._common import ProgramOptions, print_header

from .._types import Path
from ..config import Config
from ..exceptions import CliException, ForgeApiOperationFailed
from ..forge import make_client
from ..logging import get_app_logger


_logger = get_app_logger()


def _copy_custom_cert(opts: ProgramOptions, certs: tuple[Path]) -> None:
    if opts.config is None:
        raise CliException('Cannot copy custom cert without a gantry config.')

    _logger.debug('Creating %s provider certs folder.')
    certs_folder = opts.app_folder / 'certs'
    certs_folder.mkdir(mode=0o700, parents=True, exist_ok=True)

    certs_bundle = certs_folder / f'{opts.config.forge_provider}.ca-bundle'
    with certs_bundle.open('wt') as f_out:
        for cert in certs:
            _logger.debug('Appending \'%s\' to \'%s\'.', cert, certs_bundle)
            with cert.open('rt') as f_in:
                f_out.write(f_in.read())


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
        'automatically obtain this for some forge providers.'
    ),
    type=str
)
@click.option(
    '--user', '-u', 'username',
    envvar='GANTRY_FORGE_USER',
    help=(
        'The username of the account that gantry will try and connect as.'
    ),
    type=str
)
@click.option(
    '--pass', '-p', 'password',
    envvar='GANTRY_FORGE_PASS',
    help=(
        'The password of the account that gantry will try and connect as.'
    )
)
@click.option(
    '--cert', '-c', 'certs',
    multiple=True,
    help=(
        'Specify a custom TLS certificate to use with the forge provider.  '
        'This may be used multiple times if a chain of certificates need to be '
        'specified.'
    ),
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, path_type=Path)
)
@click.pass_obj
def cmd_authenticate(opts: ProgramOptions,
                     api_token: str | None,
                     username: str | None,
                     password: str | None,
                     certs: tuple[Path]) -> None:
    '''Authenticate with a software forge.

    Gantry supports both username/password and API token authentication for a
    specific forge provider.  These are mutually exclusive, and specifying an
    API token will override any username/password configuration.  This only
    needs to be done once for a new gantry installation.

    The command supports passing in the credentials as environment variables.
    Use GANTRY_FORGE_API_TOKEN to enable API token authentications.  Use
    GANTRY_FORGE_USER and GANTRY_FORGE_PASS when working with user name and
    password logins.
    '''
    config = _check_config(opts)
    if len(certs) > 0:
        _copy_custom_cert(opts, certs)

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
    except ForgeApiOperationFailed as e:
        _logger.exception(str(e), exc_info=e)
        raise CliException('Failed to get version...run with \'gantry -d\' to see traceback.')
