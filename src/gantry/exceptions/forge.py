class ForgeError(Exception):
    '''Base exception for errors thrown when working with software forges.'''


class CannotObtainForgeAuthError(ForgeError):
    '''Thrown when the forge authentication information cannot be access.'''
    def __init__(self, forge_ident: str) -> None:
        super().__init__(f'Cannot load auth info for \'{forge_ident}\' forge provider.')
