from .provider import RoutingProvider
from .traefik import TraefikRoutingProvider

PROVIDERS: dict[str, type[RoutingProvider]] = {
    'traefik': TraefikRoutingProvider
}
'''The set of available routing providers.'''
