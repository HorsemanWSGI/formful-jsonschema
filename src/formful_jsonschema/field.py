import re
import formful.form
import formful.fields
from functools import partial
from typing import Optional, Dict, ClassVar, Type, Iterable
from formful_jsonschema._fields import MultiCheckboxField, GenericFormFactory
from formful_jsonschema.validators import NumberRange
from formful_jsonschema.converter import JSONFieldParameters, converter


string_formats = {
    'default': formful.fields.StringField,
    'password': formful.fields.PasswordField,
    'date': formful.fields.DateField,
    'time': formful.fields.TimeField,
    'date-time': formful.fields.DateTimeField,
    'email': formful.fields.EmailField,
    'ipv4': formful.fields.StringField,
    'ipv6': formful.fields.StringField,
    'binary': formful.fields.FileField,
    'uri': formful.fields.URLField
}


@converter.register('string')
class StringParameters(JSONFieldParameters):

    supported = {'string'}
    allowed = {
        'format', 'pattern', 'enum', 'minLength', 'maxLength',
        'writeOnly', 'default', 'contentMediaType', 'contentEncoding'
    }

    def __init__(self, type, name, required, validators, attributes, **kwargs):
        self.format = attributes.pop('format', 'default')
        super().__init__(
            type, name, required, validators, attributes, **kwargs)

    def get_factory(self):
        if self.factory is not None:
            return self.factory
        if 'choices' in self.attributes:
            return formful.fields.SelectField
        return string_formats[self.format]

    @classmethod
    def extract(cls, params: dict, available: set):
        validators = []
        attributes = {}
        if {'minLength', 'maxLength'} & available:
            validators.append(formful.validators.Length(
                min=params.get('minLength', -1),
                max=params.get('maxLength', -1)
            ))
        if 'default' in available:
            attributes['default'] = params.get('default')
        if 'pattern' in available:
            validators.append(formful.validators.Regexp(
                re.compile(params['pattern'])
            ))
        if 'enum' in available:
            attributes['choices'] = [(v, v) for v in params['enum']]
        if 'format' in available:
            format = attributes['format'] = params['format']
            if format not in string_formats:
                raise NotImplementedError(
                    f'String format not implemented: {format}.')
            if format == 'ipv4':
                validators.append(formful.validators.IPAddress(
                    ipv4=True, ipv6=False))
            if format == 'ipv6':
                validators.append(formful.validators.IPAddress(
                    ipv4=False, ipv6=True))
            if format == 'binary':
                if 'contentMediaType' in available:
                    ctype = params['contentMediaType']
                    if isinstance(ctype, (list, tuple, set)):
                        ctype = ','.join(ctype)
                    kw = attributes.get('render_kw', {})
                    kw['accept'] = ctype
                    attributes['render_kw'] = kw

        return validators, attributes


@converter.register('integer')
@converter.register('number')
class NumberParameters(JSONFieldParameters):

    supported = {'integer', 'number'}
    allowed = {
        'enum', 'format',
        'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
        'default'
    }

    def get_factory(self):
        if self.factory is not None:
            return self.factory
        if 'choices' in self.attributes:
            return formful.fields.SelectField
        if self.type == 'integer':
            return formful.fields.IntegerField
        return formful.fields.FloatField

    @classmethod
    def extract(cls, params: dict, available: set):
        validators = []
        attributes = {}
        if default := params.get('default'):
            attributes['default'] = default
        if {'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum'} \
           & available:
            validators.append(NumberRange(
                min=params.get('minimum', None),
                max=params.get('maximum', None),
                exclusive_min=params.get('exclusiveMinimum', None),
                exclusive_max=params.get('exclusiveMaximum', None)
            ))
        if 'enum' in available:
            attributes['choices'] = [(v, v) for v in params['enum']]
        return validators, attributes


@converter.register('boolean')
class BooleanParameters(JSONFieldParameters):
    supported = {'boolean'}

    @classmethod
    def extract(cls, params: dict, available: set):
        if 'default' in available:
            return [], {'default': params['default']}
        return [], {}

    def get_factory(self):
        if self.factory is not None:
            return self.factory
        return formful.fields.BooleanField


@converter.register('array')
class ArrayParameters(JSONFieldParameters):

    supported = {'array'}
    allowed = {
        'enum', 'items', 'minItems', 'maxItems', 'default', 'definitions'
    }
    subfield: Optional[JSONFieldParameters] = None

    def __init__(self, *args, subfield=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.subfield = subfield

    def get_factory(self):
        if self.factory is not None:
            return self.factory
        if 'choices' in self.attributes:
            return MultiCheckboxField
        if isinstance(self.subfield, StringParameters):
            if self.subfield.format == 'binary':
                return partial(
                    formful.fields.MultipleFileField,
                    **self.subfield.attributes)
        elif self.subfield is None:
            raise NotImplementedError(
                "Unsupported array type : 'items' attribute required.")
        return partial(formful.fields.FieldList, self.subfield())

    @classmethod
    def extract(cls, params: dict, available: set):
        attributes = {}
        if 'minItems' in available:
            attributes['min_entries'] = params['minItems']
        if 'maxItems' in available:
            attributes['max_entries'] = params['maxItems']
        if 'default' in available:
            attributes['default'] = params['default']
        return [], attributes

    @classmethod
    def from_json_field(cls, name: str, required: bool, params: dict):
        available = set(params.keys())
        if illegal := ((available - cls.ignore) - cls.allowed):
            raise NotImplementedError(
                f'Unsupported attributes for array type: {illegal}')

        validators, attributes = cls.extract(params, available)
        if 'enum' in available:
            attributes['choices'] = [(v, v) for v in params['enum']]

        if 'items' in available and (items := params['items']):
            if ref := items.get('$ref'):
                definitions = params.get('definitions')
                if not definitions:
                    raise NotImplementedError('Missing definitions.')
                items = definitions[ref.split('/')[-1]]
            subfield = converter.lookup(items['type']).from_json_field(
                name, False, items
            )
        else:
            subfield = None
        return cls(
            params['type'],
            name,
            required,
            validators,
            attributes,
            subfield=subfield,
            label=params.get('title'),
            description=params.get('description')
        )


@converter.register('object')
class ObjectParameters(JSONFieldParameters):

    ignore = JSONFieldParameters.ignore | {
        '$id', 'id', '$schema', '$comment'
    }
    supported = {'object'}
    allowed = {'required', 'properties', 'definitions'}
    fields: Dict[str, JSONFieldParameters]
    formclass: ClassVar[Type[formful.form.BaseForm]] = formful.form.BaseForm

    def __init__(self, fields, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = fields

    def get_factory(self):
        if self.factory is not None:
            return self.factory
        return GenericFormFactory(self.fields, self.formclass)

    def get_options(self):
        # Object-types do not need root validators.
        # Validation is handled at field level.
        return self.attributes

    @classmethod
    def from_json_field(
            cls, name: str, required: bool, params: dict,
            include: Optional[Iterable] = None,
            exclude: Optional[Iterable] = None
    ):
        available = set(params.keys())
        if illegal := ((available - cls.ignore) - cls.allowed):
            raise NotImplementedError(
                f'Unsupported attributes for string type: {illegal}')

        properties = params.get('properties', None)
        if properties is None:
            raise NotImplementedError("Missing properties.")

        if include is None:
            include = set(properties.keys())
        else:
            include = set(include)  # idempotent
        if exclude is not None:
            include = include - set(exclude)

        requirements = params.get('required', [])
        fields = {}
        definitions = params.get('definitions', {})
        for property_name, definition in properties.items():
            if property_name not in include:
                continue
            if ref := definition.get('$ref'):
                if not definitions:
                    raise NotImplementedError('Missing definitions.')
                definition = definitions[ref.split('/')[-1]]
            if type_ := definition.get('type', None):
                field = converter.lookup(type_)
                if 'definitions' in field.allowed:
                    definition['definitions'] = definitions
                fields[property_name] = field.from_json_field(
                    property_name,
                    property_name in requirements, definition
                )
            else:
                raise NotImplementedError(
                    f'Undefined type for property {property_name}'
                )
        validators, attributes = cls.extract(params, available)
        if validators:
            raise NotImplementedError(
                "Object-types can't have root validators")
        return cls(
            fields,
            params['type'],
            name,
            required,
            validators,
            attributes,
            label=params.get('title'),
            description=params.get('description')
        )
