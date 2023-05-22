class ForgeError(Exception):
    '''Base exception for errors thrown when working with software forges.'''
    def __init__(self, forge: str, msg: str) -> None:
        self._forge = forge
        super().__init__(f'{forge} :: {msg}')

    @property
    def forge(self) -> str:
        return self._forge


class CannotObtainForgeAuthError(ForgeError):
    '''Thrown when the forge authentication information cannot be access.'''
    def __init__(self, forge_ident: str) -> None:
        super().__init__(forge_ident, 'Cannot load auth info.')


class ForgeApiOperationFailed(ForgeError):
    '''Thrown when an API operation has failed.'''
    def __init__(self, forge_ident: str, msg: str) -> None:
        super().__init__(forge_ident, msg)


class ForgeOperationNotSupportedError(ForgeError):
    '''Thrown when the request operation is not supported for this particular forge client.'''
    def __init__(self, forge_ident: str, msg: str) -> None:
        super().__init__(forge_ident, msg)


class ForgeUrlInvalidError(ForgeError):
    '''Thrown when the URL for a forge is invalid.'''
    def __init__(self, forge: str, url: str) -> None:
        super().__init__(forge, f'\'{url}\' must be a valid URL and use \'https\'.')
