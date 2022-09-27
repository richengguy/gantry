from pathlib import Path
from typing import Callable

import click
from click.testing import CliRunner

from gantry import cli
from gantry._compose_spec import ComposeFile

import pytest
from pytest import Config

from ruamel.yaml import YAML


@pytest.fixture()
def compile_compose_file(samples_folder: Path, tmp_path: Path) -> Callable[[str, str], ComposeFile]:

    def _run_command(folder: str, sample: str) -> ComposeFile:
        runner = CliRunner()
        sample_path = samples_folder / folder / sample
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(cli.main, ['build-compose', '-s', sample_path.as_posix()])
            compose_file = Path(td) / 'services.docker' / 'docker-compose.yml'

            click.echo(result.stdout)
            assert result.exit_code == 0
            assert compose_file.exists()

            yaml = YAML()
            with compose_file.open('rt') as f:
                return yaml.load(f)

    return _run_command


@pytest.fixture()
def compile_services(samples_folder: Path, tmp_path: Path) -> Callable[[str, str], Path]:

    def _run_command(folder: str, sample: str) -> Path:
        runner = CliRunner()
        sample_path = samples_folder / folder / sample
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(cli.main, ['build-compose', '-s', sample_path.as_posix()])
            output_path = Path(td) / 'services.docker'

            click.echo(result.stdout)
            assert result.exit_code == 0
            assert (output_path / 'docker-compose.yml').exists()

            return output_path

    return _run_command


@pytest.fixture()
def samples_folder(pytestconfig: Config) -> Path:
    return pytestconfig.invocation_params.dir / 'test' / 'samples'
