from gantry._types import Path
from gantry.config import Config


def test_basic_config(samples_folder: Path) -> None:
    yaml_file = samples_folder / 'configs' / 'basic.yml'
    config = Config(yaml_file)

    assert config.forge_owner == 'some-org'
    assert config.forge_provider == 'gitea'
    assert config.forge_url == 'https://gitea.example.com'

    assert config.registry_namespace == 'some-org'
    assert config.registry_url == 'https://gitea.example.com'


def test_container_repo_config(samples_folder: Path) -> None:
    yaml_file = samples_folder / 'configs' / 'container-repo.yml'
    config = Config(yaml_file)

    assert config.forge_owner == 'some-org'
    assert config.forge_provider == 'gitea'
    assert config.forge_url == 'https://gitea.example.com'

    assert config.registry_namespace == 'my-namespace'
    assert config.registry_url == 'https://containers.example.com'
