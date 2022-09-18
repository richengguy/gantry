from pathlib import Path

from click.testing import CliRunner

from gantry import cli

import pytest

from ruamel.yaml import YAML


@pytest.mark.parametrize(
    ('sample', 'expected'),
    [
        ('traefik-default', '/var/run/docker.sock'),
        ('traefik-custom-socket', '/run/users/1001/docker.sock')
    ]
)
def test_router_args(sample: str, expected: str, samples_folder: Path, tmp_path: Path):
    runner = CliRunner()
    default_example = samples_folder / 'router' / sample
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(cli.main, ['build-compose', '-s', default_example.as_posix()])
        compose_file = Path(td) / 'services.docker' / 'docker-compose.yml'
        assert result.exit_code == 0
        assert compose_file.exists

        yaml = YAML()
        with compose_file.open('rt') as f:
            compose_spec = yaml.load(f)

        volumes = compose_spec['services']['proxy']['volumes']
        assert volumes[0] == f'{expected}:/var/run/docker.sock:ro'
