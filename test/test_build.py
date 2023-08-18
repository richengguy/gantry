from pathlib import Path

from click.testing import CliRunner

from gantry import cli
from gantry.build_manifest import BuildManifest


def test_cannot_provide_both_tag_and_build_id(samples_folder: Path) -> None:
    path = samples_folder / 'service-definition' / 'build-args'

    runner = CliRunner()
    result = runner.invoke(cli.main, ['build', '-t', '1', '-n', '1', str(path)])
    assert result.exit_code != 0
    assert 'Cannot specify both "--tag" and "--build-number".' in result.stdout


def test_manifest_generation(samples_folder: Path, tmp_path: Path) -> None:
    path = samples_folder / 'service-definition' / 'build-args'

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(cli.main, ['build', '--tag', '123', '--skip-build', str(path)])
        assert result.exit_code == 0

        manifest_file = Path(td) / 'build' / 'services.dockerfiles' / 'manifest.json'
        assert manifest_file.exists()

        manifest = BuildManifest.load(manifest_file)
        images = list(manifest.image_entries())
        assert manifest.num_entries() == len(images)

        assert images[0].image == 'no-args:123'
        assert images[0].source == Path('build-args/no-args/Dockerfile')

        assert images[1].image == 'with-args:123'
        assert images[1].source == Path('build-args/with-args/Dockerfile')
