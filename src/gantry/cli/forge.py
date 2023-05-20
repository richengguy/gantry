import click


@click.group('forge')
def cmd() -> None:
    '''Interact with git repos and artifact stores.'''


@cmd.command('auth')
def cmd_authenticate() -> None:
    '''Authenticate with a software forge.'''
