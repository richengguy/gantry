from pathlib import Path

from click.testing import CliRunner

from gantry import cli


def test_cannot_provide_both_tag_and_build_id(samples_folder: Path) -> None:
    path = samples_folder / 'service-definition' / 'build-args'

    runner = CliRunner()
    result = runner.invoke(cli.main, ['build', '-t', '1', '-n', '1', str(path)])
    assert result.exit_code != 0
    assert 'Cannot specify both "--tag" and "--build-number".' in result.stdout
