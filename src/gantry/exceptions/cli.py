from typing import IO

import click


class CliException(click.ClickException):
    def __init__(self, message: str) -> None:
        super().__init__(message)

    def show(self, file: IO | None = None) -> None:
        click.echo(f'{click.style("Error:", bold=True, fg="red")} {self.message}')
