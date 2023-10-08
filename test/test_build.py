from pathlib import Path

from click.testing import CliRunner

from gantry import cli
from gantry.build_manifest import BuildManifest
from gantry.targets import MANIFEST_FILE


def test_cannot_provide_both_tag_and_build_id(samples_folder: Path) -> None:
    path = samples_folder / 'service-definition' / 'build-args'

    runner = CliRunner()
    result = runner.invoke(cli.main, ['build', '-t', '1', '-n', '1', 'image', str(path)])
    assert result.exit_code != 0
    assert 'Cannot specify both "--tag" and "--build-number".' in result.stdout


def test_manifest_generation(samples_folder: Path, tmp_path: Path) -> None:
    path = samples_folder / 'service-definition' / 'build-args'

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        args = ['build', '--tag', '123', '-X', 'skip-build', 'image', str(path)]
        result = runner.invoke(cli.main, args)
        print(result.stdout)
        assert result.exit_code == 0

        manifest_file = Path(td) / 'build' / 'services.image' / MANIFEST_FILE
        assert manifest_file.exists()

        manifest = BuildManifest.load(manifest_file)
        images = list(manifest.image_entries())
        assert manifest.num_entries() == len(images)

        assert images[0].image == 'no-args:123'
        assert images[0].source == Path('build-args/no-args/Dockerfile')

        assert images[1].image == 'with-args:123'
        assert images[1].source == Path('build-args/with-args/Dockerfile')


def test_custom_manifest_name(samples_folder: Path, tmp_path: Path) -> None:
    path = samples_folder / 'service-definition' / 'build-args'

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        args = ['build', '-X', 'skip-build', '-m', 'custom-name', 'image', str(path)]
        result = runner.invoke(cli.main, args)
        print(result.stdout)
        assert result.exit_code == 0

        manifest_file = Path(td) / 'build' / 'services.image' / MANIFEST_FILE
        manifest = BuildManifest.load(manifest_file)
        assert manifest.name == 'custom-name'


def test_multi_service_group_compose(samples_folder: Path, tmp_path: Path) -> None:
    group1 = samples_folder / 'service-definition' / 'build-args'
    group2 = samples_folder / 'service-definition' / 'entrypoints'

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        args = ['build', '--tag', '123', 'compose', str(group1), str(group2)]
        result = runner.invoke(cli.main, args)
        print(result.stdout)
        assert result.exit_code == 0

        manifest_json = Path(td) / 'build' / 'services.compose' / MANIFEST_FILE
        manifest = BuildManifest.load(manifest_json)

        assert manifest.name == 'services-compose'
        assert manifest.num_entries() == 2

        entries = list(manifest.docker_compose_entries())
        assert entries[0].compose_file == Path('build-args/docker-compose.yml')
        assert entries[1].compose_file == Path('entrypoints/docker-compose.yml')

        assert (Path(td) / 'build' / 'services.compose' / 'build-args').exists()
        assert (Path(td) / 'build' / 'services.compose' / 'entrypoints').exists()


def test_multi_service_group_image(samples_folder: Path, tmp_path: Path) -> None:
    group1 = samples_folder / 'service-definition' / 'build-args'
    group2 = samples_folder / 'service-definition' / 'entrypoints'

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        args = ['build', '--tag', '123', '-X', 'skip-build', 'image', str(group1), str(group2)]
        result = runner.invoke(cli.main, args)
        print(result.stdout)
        assert result.exit_code == 0

        manifest_json = Path(td) / 'build' / 'services.image' / MANIFEST_FILE
        manifest = BuildManifest.load(manifest_json)

        assert manifest.name == 'services-image'
        assert manifest.num_entries() == 5

        images = list(manifest.image_entries())
        assert images[0].image == 'no-args:123'
        assert images[1].image == 'with-args:123'

        assert images[2].image == 'complex-entrypoint:123'
        assert images[3].image == 'default:123'
        assert images[4].image == 'string-entrypoint:123'
