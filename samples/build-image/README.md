# 'gantry' Build Image
This shows how gantry can be used to build Docker images from a service group.
The `gantry build` command connects to the local Docker socket and builds images
for each service in the service group.  See [_build.sh](_build.sh) for how this
is done.

> Note: This example doesn't host any web services.  The HTTP/HTTPS entrypoints
> and networking configuration are still specified because it's required by the
> gantry service group spec.
