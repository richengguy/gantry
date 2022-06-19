from pathlib import Path

import pytest
from pytest import Config


@pytest.fixture()
def samples_folder(pytestconfig: Config) -> Path:
    return pytestconfig.invocation_params.dir / 'test' / 'samples'
