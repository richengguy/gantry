from pathlib import Path
from typing import NamedTuple


class ProgramOptions(NamedTuple):
    services_path: Path


PathLike = Path | str
