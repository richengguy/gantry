import json

import click

from .._types import Path
from ..schemas import Schema, get_schema


@click.group("schemas")
def cmd():
    """Access the schemas that validate service groups and definitions."""


@cmd.command("dump")
@click.argument(
    "name", metavar="NAME", type=click.Choice([schema.value for schema in Schema])
)
def schemas_dump(name: str):
    """Prints a schema in JSON format to stdout.

    The list of valid schema names can be found with `gantry schemas list`.
    """
    schema = Schema(name)
    contents = get_schema(schema)
    click.echo(json.dumps(contents, indent=4))


@cmd.command("export")
@click.option(
    "--output",
    "-o",
    default="./schemas",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Output folder for the schema files.  Defaults to './schemas'.",
)
def schemas_export(output: Path):
    """Export the JSON schema files used by gantry."""
    output.mkdir(exist_ok=True)
    for schema in Schema:
        contents = get_schema(schema)
        with (output / f"{schema.value}.json").open("wt") as f:
            json.dump(contents, f, indent=4)


@cmd.command("list")
def schemas_list():
    """List the schemas used by gantry."""
    for schema in Schema:
        click.echo(schema.value)
