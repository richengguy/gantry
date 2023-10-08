import click

from rich.prompt import Prompt
from rich.console import Console

from ._common import ProgramOptions, print_header
from ._git import clone_repo

from .._types import Path
from ..build_manifest import BuildManifest
from ..config import Config
from ..exceptions import CliException, GantryException
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
    metavar='TOKEN',
    envvar='GANTRY_FORGE_API_TOKEN',
    help=(
        'An API token that is used to access the forge.  Depending on the '
        'provider, the token may require specific scopes/permissions to work '
        'correctly.'
    ),
    type=str
)
@click.option(
    '--user', '-u', 'username',
    metavar='USERNAME',
    envvar='GANTRY_FORGE_USER',
    help=(
        'An account user name.  Required for Basic authentication.'
    ),
    type=str
)
@click.option(
    '--pass', '-p', 'password',
    metavar='PASSWORD',
    envvar='GANTRY_FORGE_PASS',
    help=(
        'An account password.  Required for Basic authentication.'
    )
)
@click.option(
    '--cert', '-c', 'certs',
    multiple=True,
    help=(
        'Specify a custom TLS certificate to use with the forge provider.  '
        'This may be used multiple times if a chain of certificates needs to '
        'be specified.'
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
    console = Console()
    config = _check_config(opts)

    has_username = username is not None
    has_password = password is not None

    basic_auth = all([has_username, has_password])
    api_auth = all([has_username, api_token])

    if basic_auth and api_auth:
        console.print(
            '[bold red]\u274c[/bold red] Cannot specify both an API token and '
            'password.'
        )
        raise CliException('Invalid options.')

    if has_username and not has_password:
        raise CliException('Must provide a password with a username.')

    if not has_username and has_password:
        raise CliException('Must provide a username with a password.')

    if not basic_auth and not api_auth:
        result = Prompt.ask('[grey30]>[/grey30] Authentication Type', choices=['basic', 'token'])
        username = Prompt.ask('   [grey30]-[/grey30] Username')
        match result:
            case 'basic':
                password = Prompt.ask('   [grey30]-[/grey30] Password', password=True)
            case 'token':
                api_token = Prompt.ask('   [grey30]-[/grey30] API Token', password=True)
            case _:
                raise CliException(f'Unknown option {result}.')
    else:
        auth_type = 'basic' if basic_auth else 'api_auth'
        console.print(f'[grey30]>[/grey30] Configurating \'{auth_type}\' authentication.')

    if len(certs) > 0:
        _copy_custom_cert(opts, certs)

    client = make_client(config, opts.app_folder)

    if api_token is not None:
        client.set_token_auth(user=username, api_token=api_token)  # type: ignore
    elif username is not None and password is not None:
        client.set_basic_auth(user=username, passwd=password)
    else:
        raise CliException('Unknown authentication type.')

    try:
        client.get_server_version()
        client.authenticate_with_container_registry()
        console.print('[green]\u2713[/green] Authenticated')
    except GantryException as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Authentication failed...run with \'gantry -d\' to see traceback.')


@cmd.command('push')
@click.option(
    '--dry-run', '-n',
    is_flag=True,
    help='Parse the manifest but don\'t actually push anything up to the software forge.'
)
@click.argument(
    'manifest_path',
    metavar='MANIFEST',
    type=click.Path(file_okay=True, dir_okay=False, exists=True, path_type=Path)
)
@click.pass_obj
def cmd_push(opts: ProgramOptions, dry_run: bool, manifest_path: Path) -> None:
    '''Push built container images to the forge's registry.

    The images to push are stored in a MANIFEST file that's generated by
    'gantry build'.
    '''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    try:
        manifest = BuildManifest.load(manifest_path)

        console = Console()
        if dry_run:
            console.print(
                '[bold yellow]:double_exclamation_mark:[/bold yellow] '
                'Dry run; no push will occur.'
            )

        for entry in manifest.image_entries():
            with console.status(f'Pushing [bold]{entry.image}[/bold]'):
                if not dry_run:
                    client.push_image(entry.image)
                console.print(
                    f'[bold green]\u2713[/bold green] Pushed [bold]{entry.image}[/bold]',
                    highlight=False)
    except GantryException as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Push failed...run with \'gantry -d\' to see traceback.')


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
    except GantryException as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Failed to get version...run with \'gantry -d\' to see traceback.')


@cmd.group('repos')
def cmd_repos() -> None:
    '''Manage service repos on the software forge.

    The 'repos' commands allows gantry to create git repos on a remote software
    forge.  All operations are done using the service account that was used with
    the 'auth' commnd.
    '''


@cmd_repos.command('clone')
@click.argument('name')
@click.argument('dest', type=click.Path(exists=False))
@click.pass_obj
def cmd_repos_clone(opts: ProgramOptions, name: str, dest: Path) -> None:
    '''Clone a service repo into a new directory.

    Clone the service repo NAME to DEST.
    '''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    console = Console()
    console.print('Fetching the clone URL...')

    try:
        clone_url = client.get_clone_url(name, 'https')
        _logger.debug('Clone URL: %s', clone_url)
        _logger.debug('Destination: %s', dest)
    except GantryException as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Failed to clone repo...run with \'gantry -d\' to see traceback.')

    clone_repo(client, clone_url, dest)
    console.print(f'[bold green]\u2713[/bold green] Repo cloned to `{dest}`.')


@cmd_repos.command('create')
@click.option(
    '--description', '-d',
    help='An optional description for the new repo.',
    type=str
)
@click.argument('name')
@click.pass_obj
def cmd_repos_create(opts: ProgramOptions, description: str | None, name: str) -> None:
    '''Create a new service repo.

    This will create a new, empty repo called NAME in the service organization.
    '''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    console = Console()
    try:
        full_name = client.create_repo(name, description)
        console.print(f'[bold green]\u2713[/bold green] Created \'{full_name}\'')
    except GantryException as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Failed to create repo...run with \'gantry -d\' to see traceback.')


@cmd_repos.command('delete')
@click.argument('name')
@click.confirmation_option(prompt='Are you sure you want to delete this repo?')
@click.pass_obj
def cmd_repos_delete(opts: ProgramOptions, name: str) -> None:
    '''Delete an existing service repo.

    This is a destructive action and *will* remove NAME from the service
    organization.
    '''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    console = Console()
    try:
        _logger.debug('Deleting \'%s\' from the service account.', name)
        full_name = client.delete_repo(name)
        console.print(f':wastebasket: Deleted \'{full_name}\'')
    except GantryException as e:
        _logger.exception("%s", str(e), exc_info=e)
        raise CliException('Failed to delete repo...run with \'gantry -d\' to see traceback.')


@cmd_repos.command('list')
@click.pass_obj
def cmd_repos_list(opts: ProgramOptions) -> None:
    '''List all repos in the service account.'''
    config = _check_config(opts)
    client = make_client(config, opts.app_folder)

    console = Console()
    try:
        repos = client.list_repos()
        console.print(f'Org: [i]{config.forge_owner}[/i]')
        console.print('Repos:')
        for repo in repos:
            console.print(f' - [i]{repo}[/i]')
    except GantryException as e:
        _logger.exception('%s', str(e), exc_info=e)
        raise CliException('Failed to list repos...run with \'gantry -d\' to see traceback.')
