import json
from pathlib import Path

from gantry.build_manifest import BuildManifest, DockerComposeEntry, ImageEntry


def test_create_manifest(tmp_path: Path) -> None:
    manifest = BuildManifest()
    manifest.append_entry(DockerComposeEntry(Path('./folder/docker-compose.yml'), False))
    manifest.append_entry(ImageEntry('repo/image:1234', Path('./folder/Dockerfile')))

    manifest_json = tmp_path / 'manifest.json'
    manifest.save(manifest_json)

    with manifest_json.open('rt') as f:
        items = json.load(f)

    assert len(items['contents']) == 2

    assert items['contents'][0]['type'] == 'docker-compose'
    assert items['contents'][0]['compose-file'] == './folders/docker-compose.yml'
    assert not items['contents'][0]['is-deployable']

    assert items['contents'][1]['type'] == 'image'
    assert items['contents'][1]['image'] == 'repo/image:1234'
    assert items['contents'][1]['source'] == './folder/Dockerfile'


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
