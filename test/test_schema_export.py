import json
from pathlib import Path

from click.testing import CliRunner

from gantry import cli
from gantry.schemas import Schema, get_schema

import pytest


@pytest.mark.parametrize("schema", [Schema.SERVICE, Schema.SERVICE_GROUP])
def test_schema_dump(schema: Schema):
    runner = CliRunner()
    result = runner.invoke(cli.main, ["schemas", "dump", schema.value])
    assert result.exit_code == 0

    # Dumped JSON schema and directly loaded schema should be identical.
    contents = get_schema(schema)
    parsed = json.loads(result.output)
    assert contents == parsed


@pytest.mark.parametrize("schema", [Schema.SERVICE, Schema.SERVICE_GROUP])
def test_schema_export(schema: Schema, tmp_path: Path):
    # NOTE: Using parameterization to make it easier to isolate issues by
    # checking each schema type separately.

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(cli.main, ["schemas", "export"])
        assert result.exit_code == 0

        # Exported JSON file and directly loaded schema should be identical.
        json_schema = Path(td) / "schemas" / f"{schema.value}.json"
        with json_schema.open("rt") as f:
            parsed = json.load(f)

        contents = get_schema(schema)
        assert contents == parsed


def test_schema_list():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["schemas", "list"])
    assert result.exit_code == 0

    schemas = result.output.splitlines()
    assert len(schemas) == 4
    assert schemas[0] == Schema.BUILD_MANIFEST.value
    assert schemas[1] == Schema.CONFIG.value
    assert schemas[2] == Schema.SERVICE.value
    assert schemas[3] == Schema.SERVICE_GROUP.value
