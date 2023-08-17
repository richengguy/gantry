from dataclasses import dataclass
from enum import Enum
import json
from typing import Iterator, cast

from ._types import Path, PathLike
from .exceptions import (
    BuildManifestException,
    BuildManifestBadFilePathError,
    BuildManifestValidationError
)
from .schemas import Schema, validate_object


class EntryType(str, Enum):
    '''The type of entry within a build manifest.'''
    DOCKER_COMPOSE = 'docker-compose'
    '''The entry is a service folder converted into a Docker Compose format.'''
    IMAGE = 'image'
    '''The entry is a service container image.'''


@dataclass
class Entry:
    '''Base class of all manifest entries.'''
    type: EntryType
    '''The type of the entry.'''

    def to_dict(self) -> dict:
        return {'type': self.type.value}


@dataclass
class DockerComposeEntry(Entry):
    '''A manifest entry for a service converted into a Docker Compose format.'''
    compose_file: Path
    '''Path to the docker-compose.yml file.'''
    is_deployable: bool
    '''Indicate if the compose file, and it's parent folder, are deployable.'''

    def __post_init__(self) -> None:
        if self.compose_file.name != 'docker-compose.yml':
            raise BuildManifestBadFilePathError('compose-file',
                                                'docker-compose.yml',
                                                self.compose_file.name)

    @property
    def source_folder(self) -> Path:
        '''Path to the folder containing the docker-compose.yml file.'''
        return self.compose_file.parent

    def to_dict(self) -> dict:
        entry = super().to_dict()
        entry['compose-file'] = self.compose_file.as_posix()
        if not self.is_deployable:
            entry['is-deployable'] = False
        return entry


@dataclass
class ImageEntry(Entry):
    '''A manifest entry for a service container image.'''
    image: str
    '''The name of the image.'''
    source: Path
    '''Path to the Dockerfile used to build the image.'''

    def __post_init__(self) -> None:
        if self.source.name != 'Dockerfile':
            raise BuildManifestBadFilePathError('source', 'Dockerfile', self.source.name)

    @property
    def source_folder(self) -> Path:
        '''Path to the folder containing the Dockerfile.'''
        return self.source.parent

    def to_dict(self) -> dict:
        entry = super().to_dict()
        entry['image'] = self.image
        entry['source'] = self.source.as_posix()
        return entry


class BuildManifest:
    '''Defines the contents of a gantry build.'''
    def __init__(self, *, entries: list[Entry] = []) -> None:
        '''
        Parameters
        ----------
        entries : list of :class:`Entry`
            the entries to use in the manifest; defaults to an empty list
        '''
        self._entries: list[Entry] = entries

    def append_entry(self, entry: Entry) -> None:
        '''Add an entry to the end of the manifest.

        Parameters
        ----------
        entry : :class:`Entry`
            a build manifest entry
        '''
        self._entries.append(entry)

    def docker_compose_entries(self) -> Iterator[DockerComposeEntry]:
        '''Return all Docker Compose entries in the manifest.

        Yields
        ------
        :class:`DockerComposeEntry`
            a Docker Compose entry from the manifest
        '''
        for entry in self._entries:
            if entry.type == EntryType.DOCKER_COMPOSE:
                yield cast(DockerComposeEntry, entry)

    def image_entries(self) -> Iterator[ImageEntry]:
        '''Return all image entries in the manifest.

        Yields
        ------
        :class:`ImageEntry`
            an image entry from the manifest
        '''
        for entry in self._entries:
            if entry.type == EntryType.IMAGE:
                yield cast(ImageEntry, entry)

    def num_entries(self) -> int:
        '''The number of entries in the manifest.'''
        return len(self._entries)

    def save(self, path: PathLike) -> None:
        '''Save the manifest to a file.

        Parameters
        ----------
        path : path-like object
            location to save the manifest
        '''
        manifest = {
            'type': 'gantry-manifest',
            'contents': [entry.to_dict() for entry in self._entries]
        }

        path = Path(path)
        with path.open('wt') as f:
            json.dump(manifest, f, indent=4)

    @staticmethod
    def load(path: PathLike) -> 'BuildManifest':
        '''Load the build manifest from a file.

        Parameters
        ----------
        path : Path-like object
            path to the manifest file

        Returns
        -------
        :class:`BuildManifest`
            the build manifest

        Raises
        ------
        :exc:`BuildManifestValidationError`
            if the build manifest could not be validated
        '''
        path = Path(path)
        with path.open('rt') as f:
            parsed = json.load(f)

        errors = validate_object(parsed, Schema.BUILD_MANIFEST)
        if len(errors) == 0:
            raise BuildManifestValidationError(errors)

        manifest = BuildManifest()
        item: dict
        for item in parsed['contents']:
            match item['type']:
                case EntryType.DOCKER_COMPOSE:
                    manifest.append_entry(
                        DockerComposeEntry(
                            EntryType.DOCKER_COMPOSE,
                            Path(item['compose-file']),
                            item.get('is-deployable', True)
                        )
                    )
                case EntryType.IMAGE:
                    manifest.append_entry(
                        ImageEntry(
                            EntryType.IMAGE,
                            item['image'],
                            Path(item['source'])
                        )
                    )
                case _:
                    BuildManifestException(f'Unknown item type "{item["type"]}".')

        return manifest
