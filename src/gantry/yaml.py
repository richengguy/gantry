from io import StringIO
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ._compose_spec import _ComposeBase


class YamlSerializer:
    """Serialize dictionaries to YAML-encoded strings or files."""

    def __init__(self, *, show_header=True) -> None:
        """Initialize the serializer.

        Parameters
        ----------
        show_header : bool, optional
            output a header in the generated YAML output, by default True
        """
        self._yaml = YAML()
        self._yaml.compact(seq_seq=False, seq_map=False)
        self._yaml.indent(mapping=4, sequence=6, offset=4)
        self._yaml.default_flow_style = False

        self._header = "\n".join(
            ["This file has been automatically generated.", "DO NOT MODIFY", " "]
        )

        self._show_header = show_header

    def to_string(self, data: dict | _ComposeBase) -> str:
        """Convert a dictionary to a YAML-encoded string.

        Parameters
        ----------
        data : dict
            dictionary to convert

        Returns
        -------
        str
            string representation
        """
        output = _prep_data(
            cast(dict, data), self._header if self._show_header else None
        )
        with StringIO() as s:
            self._yaml.dump(output, s)
            return s.getvalue()

    def to_file(self, data: dict | _ComposeBase, path: Path):
        """Serializes a dictionary to some file.

        Parameters
        ----------
        data : dict
            dictionary to convert
        path : Path
            path to file location
        """
        output = _prep_data(
            cast(dict, data), self._header if self._show_header else None
        )
        with path.open("wt") as f:
            self._yaml.dump(output, f)


def _prep_data(data: dict, header: str | None = None) -> CommentedMap:
    """Prepare data for serialization.

    Parameters
    ----------
    data : dict
        dictionary to serialize
    header : str | None, optional
        a header string to include in the output, by default None

    Returns
    -------
    CommentedMap
        processed data
    """
    prepped_data = _prep_dict(data)

    if header:
        prepped_data.yaml_set_start_comment(header)

    return prepped_data


def _prep_dict(data: dict) -> CommentedMap:
    """Converts an dictionary into its ruamel.yaml commented equivalent.

    Parameters
    ----------
    data : dict
        a dictionary to convert

    Returns
    -------
    CommentedMap
        the coverted entry
    """
    out = CommentedMap()
    for key, value in data.items():
        match value:
            case dict(value):
                out[key] = _prep_dict(value)
            case list(value):
                out[key] = _prep_list(value)
            case _:
                out[key] = value

    return out


def _prep_list(data: list) -> CommentedSeq:
    """Converts a list into its ruamel.yaml commented equivalent.

    Parameters
    ----------
    data : list
        a list to convert

    Returns
    -------
    CommentedSeq
        the converted list
    """
    out = CommentedSeq()

    for item in data:
        entry: Any
        match item:
            case dict(item):
                entry = _prep_dict(item)
            case list(item):
                entry = _prep_list(item)
            case _:
                entry = item
        out.append(entry)

    return out
