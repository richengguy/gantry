class TraefikConfig:
    """Helps generate the labels used to configure Traefik."""

    def __init__(self) -> None:
        self._enable_tls: bool = False
        self._port: int | None = None
        self._routes: list[str] | None = None
        self._service: str | None = None

    def add_route(self, route: str) -> None:
        """Add a route to the HTTP router.

        Parameters
        ----------
        route : str
            the path prefix to add
        """
        if self._routes is None:
            self._routes = list()
        if route in self._routes:
            raise ValueError(f"Already defined route `{route}`.")
        self._routes.append(route)

    def set_enable_tls(self, enable_tls: bool) -> None:
        """Enable TLS termination on this service.

        Parameters
        ----------
        enable_tls : bool
            determines if TLS termination is enabled
        """
        self._enable_tls = enable_tls

    def set_port(self, port: int) -> None:
        """Specify the port the service listens on.

        Parameters
        ----------
        port : int
            the port the service uses
        """
        self._port = port

    def set_service(self, service: str) -> None:
        """Specify the service traefik should attach to."""
        self._service = service

    def to_labels(self, name: str) -> dict[str, str | int | bool]:
        """Generate the container labels used for traefik configuration.

        Parameters
        ----------
        name : str
            name of the container/service the labels are for

        Returns
        -------
        dict
            a dictionary of labels
        """
        labels: dict[str, str | int | bool] = {"traefik.enable": True}

        if port := self._port:
            labels[f"traefik.http.services.{name}.loadbalancer.server.port"] = port

        if routes := self._routes:
            route_str = " || ".join(f"PathPrefix(`{route}`)" for route in routes)
            labels[f"traefik.http.routers.{name}.rule"] = route_str

        if service := self._service:
            labels[f"traefik.http.routers.{name}.service"] = service

        if self._enable_tls:
            labels[f"traefik.http.routers.{name}.tls"] = True

        return labels
