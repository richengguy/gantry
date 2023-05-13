from pathlib import Path
from typing import NamedTuple


PathLike = Path | str


class ProgramOptions(NamedTuple):
    services_path: Path
