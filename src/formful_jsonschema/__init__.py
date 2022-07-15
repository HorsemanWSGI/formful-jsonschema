import formful.form
from formful_jsonschema.field import ObjectParameters
from typing import Dict, Iterable, Optional


JSONSchema = Dict


def schema_fields(schema: JSONSchema,
                  include: Optional[Iterable[str]] = None,
                  exclude: Optional[Iterable[str]] = None):
    root = ObjectParameters.from_json_field(
        None, False, schema,
        include=include, exclude=exclude)
    return root.fields


class Form(formful.form.BaseForm):

    def __init__(self, *args, **kwargs):
        self.form_errors = []  # this exists in 3.0a1
        super().__init__(*args, **kwargs)

    @classmethod
    def from_schema(
            cls, schema: JSONSchema,
            include: Optional[Iterable[str]] = None,
            exclude: Optional[Iterable[str]] = None):
        return cls(schema_fields(schema, include, exclude))
