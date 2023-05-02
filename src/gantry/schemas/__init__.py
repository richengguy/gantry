from enum import Enum
import importlib.resources
import json
from typing import Iterator

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError


class Schema(Enum):
    '''Enumeration of available schemas.'''
    SERVICE = 'service'
    SERVICE_GROUP = 'service_group'


def get_schema(schema: Schema) -> dict:
    '''Retrieve a service defintion schema.

    Parameters
    ----------
    schema: Schema
        the schema to load

    Returns
    -------
    dict
        a dictionary with the schema in JSON Schema format
    '''
    schema_file = f'{schema.value}.json'
    resource = importlib.resources.files(__package__).joinpath(schema_file)
    with importlib.resources.as_file(resource) as path:
        with path.open() as f:
            return json.load(f)


def validate_object(instance: dict, schema: Schema) -> list[ValidationError]:
    '''Validate an object against some schema.

    Parameters
    ----------
    instance : dict
        instance of the object being validated
    schema : Schema
        schema used for validation
    '''
    schema_repr = get_schema(schema)
    validator = Draft7Validator(schema_repr)
    errors: Iterator[ValidationError] = validator.iter_errors(instance)
    return sorted(errors, key=lambda e: e.json_path)
