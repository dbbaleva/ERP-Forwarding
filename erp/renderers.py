import sys
import re
from formencode import (
    Invalid,
    variabledecode,
    validators
)
import formencode
from webhelpers2.html import tags
from webhelpers2.html.builder import HTML

from erp.schemas import DefaultSchema

basestring = (str, bytes)


class DataDict(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __contains__(self, key):
        return hasattr(self, key)

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        delattr(self, key)

    def set(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def items(self):
        return self.__dict__.items()

    def keys(self):
        return self.__dict__.keys()


############################
# Utility methods
###########################
def sync_data(model, schema, **data):
    for key, value in data.items():
        validator = schema.fields.get(key)
        if isinstance(value, list):
            if hasattr(validator, 'validators'):
                target_list = getattr(model, key)
                result_list = sync_lists(target_list, value, validator.validators[0])
                if target_list or result_list:
                    setattr(model, key, result_list)
            else:
                setattr(model, key, value)

        elif isinstance(value, dict):
            _schema = schema.fields.get(key)
            _model = getattr(model, key) or _schema.model()
            _target = getattr(model, key)

            sync_data(_model, _schema, **value)
            if not _target:
                setattr(model, key, _model)

        else:
            if hasattr(model, key):
                if hasattr(validator, 'update_model_attr'):
                    validator.update_model_attr(model, key, value)
                else:
                    setattr(model, key, value)
    return model


def sync_lists(target_list, source_list, schema):
    target_list = target_list or []
    # add or update items
    if hasattr(schema, 'model') and schema.model:
        for source_item in source_list:
            # try to find source_item in target_list - result as target_item
            from sqlalchemy.inspection import inspect
            item_id = inspect(schema.model).primary_key[0].name
            target_item = _find_item(source_item, target_list, item_id)

            # if 'target_item' is found then update or delete
            if target_item:
                if source_item.get('deleted'):
                    target_list.remove(target_item)
                else:
                    sync_data(target_item, schema, **source_item)

            # otherwise then append it to target_list
            else:
                target_item = sync_data(schema.model(), schema, **source_item)
                target_list.append(target_item)

    return target_list


def decode_request_data(request):
    if request.method == "POST":
        params = request.POST
    else:
        params = request.params

    return variabledecode.variable_decode(params)


def _find_item(item, list_, id='id'):
    item_id = _get_item_id(item, id)
    for data in list_:
        data_id = _get_item_id(data, id)
        if data_id and item_id == data_id:
            return data

    return None


def _get_item_id(item, id='id'):
    if hasattr(item, id):
        return str(getattr(item, id) or '').strip()
    if id in item:
        return str(item[id] or '').strip()

    return None


class Form(object):
    def __init__(self, request, schema, model=None):
        self.request = request
        self.schema = schema
        self.model = model
        self.errors = {}
        self.is_validated = False
        self.data = None

        # save data from model to renderer
        if model and request.method == "GET":
            self.data = self.copy_model(model, schema)

    def is_error(self, field):
        """
        Checks if individual field has errors.
        """
        return field in self.errors

    def all_errors(self):
        """
        Returns all errors in a single list.
        """
        if isinstance(self.errors, basestring):
            return [self.errors]
        if isinstance(self.errors, list):
            return self.errors
        errors = []
        for field in self.errors.keys():
            errors += self.errors_for(field)
        return errors

    def errors_for(self, field):
        """
        Returns any errors for a given field as a list.
        """
        errors = self.errors.get(field, [])
        if isinstance(errors, basestring):
            errors = [errors]
        return errors

    def validate(self, auto_update=True):
        """
        Runs validation on request against the model schema
        """

        if self.is_validated:
            return not self.errors

        decoded = decode_request_data(self.request)

        try:
            self.data = self.schema.to_python(decoded)
            if self.model and auto_update:
                # copy the validated data to model
                sync_data(self.model, self.schema, **self.data)
        except Invalid as e:
            self.errors = e.unpack_errors(encode_variables=True)
        except Exception as ex:
            e = sys.exc_info()[0]
            self.errors = e

        self.is_validated = True
        return not self.errors

    def copy_model(self, model, schema):
        """
        Copy model to form data
        """
        data = DataDict()
        for f, validator in schema.fields.items():
            if hasattr(model, f):
                value = getattr(model, f)
                if isinstance(validator, formencode.ForEach):
                    temp = value
                    value = []
                    if temp:
                        validator = validator.validators[0]
                        for v in temp:
                            value.append(self.copy_model(v, validator))

                elif isinstance(validator, DefaultSchema):
                    if value:
                        value = self.copy_model(value, validator)
                else:
                    value = validator.from_python(value)

                if value and isinstance(value, bytes):
                    value = value.decode('utf-8')

                data[f] = value

            else:
                data[f] = validator.if_missing

        return data

    def save_data(self):
        """
        Insert/update record to database
        """

        self.model.save(self.request)
        self.data = self.copy_model(self.model, self.schema)


class FormRenderer(object):
    jqueryval_attribute_rules = [
        "required",
        "email",
        "url",
        "date",
        "number",
        "minlength",
        "maxlength"
        "range"
    ]

    def __init__(self, form=None):
        self.form = None
        self.data = None
        self.request = None

        if form:
            self.form = form
            self.data = form.data
            self.request = form.request

            if self.data is None:
                data = decode_request_data(form.request)
                if form.schema:
                    data = form.schema.from_python(data)
                self.data = data

    def value(self, name, default=None):
        """
        Shortcut for self.data.get(name, default)
        """

        # try regex on name if has the form: 'obj.name'
        if not self.data:
            return None

        data = self.data
        result = re.search(r"(?P<obj>^[\w]+)(\-(?P<index>\d+))?\.(?P<name>[\w]+$)", name)
        if result:
            obj = result.group('obj')
            name = result.group('name')
            index = result.group('index')
            temp = data.get(obj)

            if temp:
                data = temp[int(index)] if isinstance(temp, list) else temp

        value = data.get(name, default)
        return value

    def validation_attrs(self, name):
        attrs = {}

        if not self.form:
            return attrs

        schema = self.form.schema

        # try regex on name if has the form: 'obj-index.name'
        result = re.search(r"(?P<obj>^[\w]+)(\-(?P<index>\d+))?\.(?P<name>[\w]+$)", name)

        if result:
            obj = result.group('obj')
            name = result.group('name')
            temp = schema.fields.get(obj)
            if temp:
                if hasattr(temp, 'validators'):
                    schema = temp.validators[0]
                else:
                    schema = temp

        validator = schema.fields.get(name)

        if validator is not None:
            jqval_rules = []
            vname = validator.__class__.__name__.lower()

            if validator.not_empty:
                attrs["required"] = "required"
                jqval_rules.append("required")

            if vname in self.jqueryval_attribute_rules:
                jqval_rules.append(vname)

            for rule in jqval_rules:
                attrs["data-rule-%s" % rule] = "true"

        # check for chained validators
        for validator in schema.chained_validators:
            clsname = validator.__class__.__name__
            if isinstance(validator, validators.RequireIfPresent) \
                    and clsname == 'RequireIfPresent' and validator.required == name:
                attrs.update({'required': 'required'})

        return attrs

    def begin(self, url=None, **attrs):
        """
        Creates the opening <form> tag
        """
        return tags.form(url, **attrs)

    def end(self):
        """
        Creates the closing </form> tag.
        """
        return tags.end_form()

    def csrf(self, name="_csrf"):
        """
        Get or create a new CSRF token and returns CSRF hidden input.
        """
        token = self.request.session.get_csrf_token()
        if token is None:
            token = self.request.session.new_csrf_token()

        return self.hidden(name, token)

    def hidden_tag(self, *names):
        """
        Convenience for printing all hidden fields in a form inside a
        hidden DIV. Will also render the CSRF hidden field.
        """
        inputs = [self.hidden(name) for name in names]
        inputs.append(self.csrf())
        return HTML.tag("div",
                        tags.literal("".join(inputs)),
                        style="display:none;")

    def text(self, name, value=None, id=None, **attrs):
        id = id or name
        attrs.update(self.validation_attrs(name))
        return tags.text(name, self.value(name, value), id, **attrs)

    def empty_text(self, name, id, **attrs):
        id = id or name
        attrs.update(self.validation_attrs(name))
        return tags.text(name, None, id, **attrs)

    def file(self, name, value=None, id=None, **attrs):
        """
        Outputs file input.
        """
        id = id or name
        attrs.update(self.validation_attrs(name))
        return tags.file(name, self.value(name, value), id, **attrs)

    def hidden(self, name, value=None, id=None, **attrs):
        """
        Outputs hidden input.
        """
        id = id or name
        # uncomment below to enable unobtrusive validation for hidden fields
        # attrs.update(self.validation_attrs(name))
        return tags.hidden(name, self.value(name, value), id, **attrs)

    def radio(self, name, value=None, checked=False, label=None, **attrs):
        """
        Outputs radio input.
        """
        checked = self.data.get(name) == value or checked
        attrs.update(self.validation_attrs(name))
        return tags.radio(name, value, checked, label, **attrs)

    def submit(self, name, value=None, id=None, **attrs):
        """
        Outputs submit button.
        """
        id = id or name
        return tags.submit(name, self.value(name, value), id, **attrs)

    def select(self, name, options, selected_value=None, id=None, **attrs):
        """
        Outputs <select> element.
        """
        id = id or name
        attrs.update(self.validation_attrs(name))
        value = self.value(name, selected_value)
        if type(value) not in (str, list, tuple, set):
            value = str(value)

        return tags.select(name, value, options, id, **attrs)

    @staticmethod
    def options(tpl_list):
        return [tags.Option(i[0], str(i[-1])) for i in tpl_list]

    def checkbox(self, name, value="1", checked=False, label=None, id=None, **attrs):
        """
        Outputs checkbox input.
        """

        id = id or name
        attrs.update(self.validation_attrs(name))
        return tags.checkbox(name, value, self.value(name), label, id, **attrs)

    def textarea(self, name, content="", id=None, **attrs):
        """
        Outputs <textarea> element.
        """
        id = id or name
        attrs.update(self.validation_attrs(name))
        return tags.textarea(name, self.value(name, content), id, **attrs)

    def password(self, name, value=None, id=None, **attrs):
        """
        Outputs a password input.
        """
        id = id or name
        attrs.update(self.validation_attrs(name))
        return tags.password(name, self.value(name, value), id, **attrs)

    def label(self, name, label=None, **attrs):
        """
        Outputs a <label> element.

        `name`  : field name. Automatically added to "for" attribute.

        `label` : if **None**, uses the capitalized field name.
        """
        if 'for_' not in attrs:
            attrs['for_'] = name
        label = label or name.capitalize()
        return HTML.tag("label", label, **attrs)

    def errorlist(self, name=None, **attrs):
        """
        Renders errors in a <ul> element. Unless specified in attrs, class
        will be "error".

        If no errors present returns an empty string.

        `name` : errors for name. If **None** all errors will be rendered.
        """

        if not self.form:
            return None

        if name is None:
            errors = self.form.all_errors()
        else:
            errors = self.form.errors_for(name)

        if not errors:
            return ''

        content = "\n".join(HTML.tag("li", error) for error in errors)

        if 'class_' not in attrs:
            attrs['class_'] = "error"

        return HTML.tag("ul", tags.literal(content), **attrs)

    def has_errors(self):
        errors = self.form.all_errors()
        return errors

    def strip_html(self, name, value=None):
        from .helpers import strip_html
        value = self.value(name, value)
        return strip_html(value)
