import json

from click.testing import CliRunner

from gantry import cli
from gantry.schemas import Schema, get_schema

import pytest


def test_schema_list():
    runner = CliRunner()
    result = runner.invoke(cli.main, ['schemas', 'list'])
    assert result.exit_code == 0

    schemas = result.output.splitlines()
    assert len(schemas) == 1
    assert schemas[0] == Schema.SERVICE.value
    assert schemas[1] == Schema.SERVICE_GROUP.value


@pytest.mark.parametrize('schema', [Schema.SERVICE, Schema.SERVICE_GROUP])
def test_schema_dump(schema: Schema):
    runner = CliRunner()
    result = runner.invoke(cli.main, ['schemas', 'dump', schema.value])
    assert result.exit_code == 0

    # Dumped JSON schema and directly loaded schema should be identical.
    contents = get_schema(schema)
    parsed = json.loads(result.output)
    assert contents == parsed
