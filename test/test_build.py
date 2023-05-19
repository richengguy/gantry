import json
from pathlib import Path

from click.testing import CliRunner

from gantry import cli


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

        with manifest_file.open('rt') as f:
            manifest = json.load(f)

        assert manifest[0]['service'] == 'no-args'
        assert manifest[0]['image'] == 'no-args:123'

        assert manifest[1]['service'] == 'with-args'
        assert manifest[1]['image'] == 'with-args:123'
