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

### Service Group

The YAML below shows an example service group definition.  It declares the
available

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

**Top-Level Properties**

| Property   | Required | Description |
| ---------- | -------- | ----------- |
| `name`     | Yes      | Service group name. |
| `network`  | Yes      | Name of the internal network used by the service group. |
| `router`   | Yes      | The router (i.e. reverse proxy) used to route requests to the host services. |
| `services` | Yes      | All of the services that are part of the service group.  Each item corresponds to a service definition folder. |

**`router` Property**

| Property   | Required | Description |
| ---------- | -------- | ----------- |
| `provider` | Yes      | The routing provider.  This must be one of *gantry*'s supported providers. |
| `config`   | Yes      | The router's configuration file.  It is relative to the `service.yml` file. |

The configuration file is processed as a Jinja template.  This allows
information about the host to be injected into the routing configuration using
Jinja's variables expansion, e.g., `{{ some_variable }}`.

| Variable          | Description |
| ------------------| ----------- |
| `service.network` | The name of the internal container network. |

### Service Definition
