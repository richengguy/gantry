# gantry - Manage containers for single-host deployments

*gantry* is a way to manage Docker containers on single-host deployments.  It is
meant to allow a small set of services to be defined in a way that agnostic to
how they're deployed (docker-compose, podman, etc.).

## Installation

The best way to install *gantry* is to use the provided
[conda](https://docs.conda.io/en/latest/) environment file.  It requires Python
3.10 and [flit](https://flit.pypa.io/en/latest/pyproject_toml.html), which the
environment file is already set up for.  Installing into a conda environment is
done by

```bash
$ conda env create
$ conda activate gantry
(gantry) $ flit install
```

You can verify the installation by running `gantry --version`.

## Defining Services

All host services are defined by a single [service group](#service-group).  It
is a collection of [service definitions](#service-definition) that all run in
their own containers on the host.  The group may also have its own set of
host-level containers, such as a reverse proxy, that are shared among all
service containers.

The service group itself is a simple folder structure, where each service
definition is a single subfolder.  For example,

```
services/
    + service.yml
    + one_service/
        + service.yml
    + another_service/
        + service.yml
        + Dockerfile
        + container-file.txt
```

The "services" folder contains the entire service group.  Its `service.yml` file
lists all of the host services along with all host-level configuration.  Each
service folder must contain its own `service.yml` file with the service
definition.

> **Note:** The name of the folder must match the name specified in the service
> definition.

The definition YAML files are all processed as Jinja templates.  Where
specified, Jinja variable syntax of the form ``{{ some_variable }}`` can be used
to inject values during processing.

### Service Group

All of a host's services are enumerated by a service group.  The group
definition also specifies the router used to route requests from the external
network to the service containers.

```yaml
name: myServiceGroup
network: internal-network
router:
    provider: traefik
    config: traefik.yml
services:
    - one_service
    - another_service
```

### Service Definition

A service is any application that runs within a container environment and can
be accessed via a URL endpoint.  By default this is the service name, e.g.
`http://my-host/my-service/`, but can be changed in the definition file.  The
service itself can be either an existing container image or a Dockerfile that
resides within the definition folder.

**Example YAML Definition**

An example definition where the `my-service` listens on `/endpoint` and uses the
`some-image:v123` image.
```yaml
name: my-service
entrypoint: /endpoint
image: some-image:v123
```

An example definition that that builds the `custom-image` service using a
Dockerfile inside of the definition folder.  The contents of the `build-args`
property are used as build arguments when building the image.
```yaml
name: custom-image
build-args:
    firstArg: foo
    secondArg: bar
```

Files can be mapped into a container using the `files` property, where
`internal` is the path within the container and `external` is on the host's file
system.  Volumes are similarly defined using the `volumes` property.  In that
case all of the paths are within the container.
```yaml
name: including-files
image: some-image:v123
files:
    config-file:
        internal: /home/ubuntu/config.ini
        external: "{{ service.folder }}"/config.ini
volumes:
    internal-storage: /storage
```

The following variables are defined when a service definition is being
processed:

| Variable          | Description |
| ------------------| ----------- |
| `service.folder`  | The path to the service definition folder. |

## Routers

Routers are used to route external traffic into the internal container network.
The choice of router is set by the `router` property in the
[service group definition](#service-group).

Each router has a configuration file specified by the `config` property that is
processed as a Jinja template.  The following variables are defined when the
group definition is being processed:

| Variable          | Description |
| ------------------| ----------- |
| `service.network` | The name of the internal container network. |

### Traefik

The `traefik` router uses [traefik proxy](https://doc.traefik.io/traefik/) for
passing information to and from the external network to the service containers.
There is minimal configuration within the service definition beyond ensuring the
dashboard can be accessed.  The router should be configured using either a YAML
or TOML [configuration file](https://doc.traefik.io/traefik/providers/file/).

The service itself has the following configuraiton arguments:

| Argument | Type | Default | Description |
| -------- | ---- | ------- | ----------- |
| `map-socket` | `bool` | `true` | Map an external Docker socket into the Traefik container as a volume mount. |
| `socket` | `string` | `/var/run/docker.sock` | Path to the Docker socket Traefik will be using. |
