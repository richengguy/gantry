class ImageTargetException(Exception):
    '''Base class for all exceptions when building container images.'''
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ClientConnectionError(ImageTargetException):
    '''Exception for any errors when connecting to the image build service.'''


class ServiceImageBuildError(ImageTargetException):
    '''Exception for when the service image failed to build.'''
