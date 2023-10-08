import json
from pathlib import Path

import pytest

from gantry.build_manifest import BuildManifest, DockerComposeEntry, ImageEntry
from gantry.exceptions import BuildManifestValidationError
from gantry.targets import MANIFEST_FILE


def test_create_manifest(tmp_path: Path) -> None:
    manifest = BuildManifest('test_create')
    manifest.append_entry(DockerComposeEntry(Path('./folder/docker-compose.yml'), False))
    manifest.append_entry(ImageEntry('repo/image:1234', Path('./folder/Dockerfile')))

    manifest_json = tmp_path / MANIFEST_FILE
    manifest.save(manifest_json)

    with manifest_json.open('rt') as f:
        items = json.load(f)

    assert items['name'] == 'test_create'

    assert len(items['contents']) == 2

    assert items['contents'][0]['type'] == 'docker-compose'
    assert items['contents'][0]['compose-file'] == 'folder/docker-compose.yml'
    assert not items['contents'][0]['is-deployable']

    assert items['contents'][1]['type'] == 'image'
    assert items['contents'][1]['image'] == 'repo/image:1234'
    assert items['contents'][1]['source'] == 'folder/Dockerfile'


def test_load_manifest(samples_folder: Path) -> None:
    manifest = BuildManifest.load(samples_folder / 'manifests' / 'example.json')
    assert manifest.num_entries() == 3

    images = list(manifest.image_entries())
    compose_files = list(manifest.docker_compose_entries())

    assert len(images) == 2
    assert images[0].image == 'repo.example.com/some-image:1234'
    assert images[0].source == Path('some-service/Dockerfile')
    assert images[1].image == 'repo/other-image:1234'
    assert images[1].source == Path('other-service/Dockerfile')

    assert len(compose_files) == 1
    assert compose_files[0].compose_file == Path('./docker-compose.yml')
    assert compose_files[0].is_deployable


def test_roundtrip_manifest(tmp_path: Path) -> None:
    manifest = BuildManifest(
        "roundtrip-test",
        entries=[
            DockerComposeEntry(Path('./first-service/docker-compose.yml'), True),
            ImageEntry('repo/image:1234', Path('./second-service/Dockerfile')),
            DockerComposeEntry(Path('./third-service/docker-compose.yml'), False)
        ])

    # Serialize
    json_file = tmp_path / MANIFEST_FILE
    manifest.save(json_file)

    # Deserialize
    loaded_manifest = BuildManifest.load(json_file)
    assert loaded_manifest.name == 'roundtrip-test'
    assert loaded_manifest.num_entries() == 3

    compose_entries = list(loaded_manifest.docker_compose_entries())
    assert len(compose_entries) == 2
    assert compose_entries[0].source_folder.name == 'first-service'
    assert compose_entries[0].is_deployable
    assert compose_entries[1].source_folder.name == 'third-service'
    assert not compose_entries[1].is_deployable

    image_entries = list(loaded_manifest.image_entries())
    assert len(image_entries) == 1
    assert image_entries[0].image == 'repo/image:1234'
    assert image_entries[0].source_folder.name == 'second-service'


def test_check_exceptions(samples_folder: Path) -> None:
    with pytest.raises(BuildManifestValidationError) as exc:
        BuildManifest.load(samples_folder / 'manifests' / 'bad-manifest.json')

    assert len(exc.value.errors) == 2
