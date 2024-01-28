from typing import TypedDict

# The three typed dictionaries below are a simplified representation of the
# Compose file specification.  The full details are at the link below:
# https://github.com/compose-spec/compose-spec/blob/master/spec.md


class _ComposeBase(TypedDict, total=False):
    pass


class ComposeBuild(_ComposeBase, total=False):
    args: dict[str, str]
    context: str
    dockerfile: str


class ComposeHealthcheck(_ComposeBase, total=False):
    test: list[str] | str
    interval: str
    timeout: str
    retries: int
    start_period: str
    start_interval: str
    disable: bool


class ComposeService(_ComposeBase, total=False):
    build: ComposeBuild
    container_name: str
    environment: dict[str, str]
    healthcheck: ComposeHealthcheck
    image: str
    labels: dict[str, str | int | bool]
    networks: list[str]
    ports: list[str]
    restart: str
    volumes: list[str]


class ComposeFile(_ComposeBase, total=False):
    services: dict[str, ComposeService]
    networks: dict[str, None]
    volumes: dict[str, None]


def define_using_image(
    image: str, container_name: str, tag: str = "latest"
) -> ComposeService:
    """Define a compose service using an existing image.

    Parameters
    ----------
    image : str
        name of the image to use
    container_name : str
        name of the container when the service is spun up
    tag : str, optional
        image's tag; default is 'latest'

    Returns
    -------
    dict
        a dictionary that defines a basic compose service; can be modified as
        needed
    """
    return {"image": ":".join([image, tag]), "container_name": container_name}


def define_using_build(
    name: str, context: str, args: dict[str, str] = {}, tag: str = "custom"
) -> ComposeService:
    """Define a compose service from a build context.

    A build context means that the service should be built from a dockerfile
    rather than pulled from a registry

    Parameters
    ----------
    name: str
        name of the
    context : str
        relative path to the folder with the dockerfile
    args : dict[str, str], optional
        optional build arguments
    tag : str, optional
        tag to attach to the generated image; defaults to 'custom'

    Returns
    -------
    dict
        a dictionary that defines a basic compose service; can be modified as
        needed
    """
    build_args: ComposeBuild = {"context": context}

    if len(args) != 0:
        build_args["args"] = args

    return {"image": ":".join([name, tag]), "container_name": name, "build": build_args}
