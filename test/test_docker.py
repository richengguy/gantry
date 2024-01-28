from gantry.docker import Docker


def test_create_high_level_client() -> None:
    d = Docker()
    # Note: This will be 'linux', even on macOS, because Docker Desktop spins
    # up a VM.
    assert d.client.version()["Os"] == "linux"


def test_create_low_level_client() -> None:
    d = Docker.create_low_level_api()
    # Note: This will be 'linux', even on macOS, because Docker Desktop spins
    # up a VM.
    assert d.version()["Os"] == "linux"
