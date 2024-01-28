from gantry.exceptions import GantryException
from gantry.services import ServiceGroupDefinition
from gantry.targets import Target

import pytest


class MockTarget(Target):
    def __init__(self, *, options: list[str] | None = None) -> None:
        super().__init__(options=options)
        self.first = "first" in self._parsed_options
        self.second = int(self._parsed_options["second"])

    def build(self, service_group: ServiceGroupDefinition) -> None: ...

    @staticmethod
    def description() -> str:
        return "Test target"

    @staticmethod
    def options() -> list[tuple[str, str]]:
        return [("first", "The first option."), ("second", "The second option.")]


def test_target_with_valid_opts() -> None:
    target = MockTarget(options=["first", "second=2"])
    assert target.first
    assert target.second == 2


@pytest.mark.parametrize("arg", ["", "abc", "first=second=3"])
def test_target_with_invalid_opts(arg: str) -> None:
    with pytest.raises(GantryException):
        MockTarget(options=[arg])
