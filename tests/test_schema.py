import hamcrest
import formful.form
import formful.fields
import jsonschema_formful.field

"""
We handle object-typed schema.
They can be fields in a form or just a plain form.
They are created just like any other field.
"""


def test_standalone_schema(person_schema):

    schema = jsonschema_formful.field.ObjectParameters.from_json_field(
        None, False, person_schema
    )

    hamcrest.assert_that(schema.fields, hamcrest.has_entries({
        "firstName": hamcrest.instance_of(
            jsonschema_formful.field.StringParameters),
        "lastName": hamcrest.instance_of(
            jsonschema_formful.field.StringParameters),
        "age": hamcrest.instance_of(
            jsonschema_formful.field.NumberParameters),
        "homepage": hamcrest.instance_of(
            jsonschema_formful.field.StringParameters
        )
    }))

    assert schema.fields["firstName"].required is True
    assert schema.fields["lastName"].required is True
    assert schema.fields["age"].required is False

    # fields are useable as unbound wtform fields
    form = formful.form.BaseForm(schema.fields)
    hamcrest.assert_that(form._fields, hamcrest.has_entries({
        "firstName": hamcrest.instance_of(
            formful.fields.StringField),
        "lastName": hamcrest.instance_of(
            formful.fields.StringField),
        "age": hamcrest.instance_of(
            formful.fields.IntegerField),
    }))


def test_schema_as_field(person_schema):

    schema = jsonschema_formful.field.ObjectParameters.from_json_field(
        'fieldname', True, person_schema
    )

    form = formful.form.BaseForm({'fieldname': schema})

    # fields are useable as unbound wtform fields
    form = formful.form.BaseForm(schema.fields)
    hamcrest.assert_that(form._fields, hamcrest.has_entries({
        "firstName": hamcrest.instance_of(
            formful.fields.StringField),
        "lastName": hamcrest.instance_of(
            formful.fields.StringField),
        "age": hamcrest.instance_of(
            formful.fields.IntegerField),
    }))
