import formencode
from formencode import validators
from formencode.api import Invalid
from erp import models


class DefaultSchema(formencode.Schema):
    """Default schema that allows and filters extra fields"""
    allow_extra_fields = True
    filter_extra_fields = True


class LoginSchema(DefaultSchema):
    username = validators.UnicodeString(not_empty=True)
    password = validators.UnicodeString(not_empty=True)


class AddressSchema(DefaultSchema):
    model = models.Address
    id = validators.Int()
    description = validators.UnicodeString(if_missing=None)
    type = validators.PlainText(if_missing=None)
    deleted = validators.StringBool(if_missing='no')

    chained_validators = [
        validators.RequireIfPresent('description', present='type'),
        validators.RequireIfPresent('type', present='description')
    ]


class PhoneSchema(DefaultSchema):
    model = models.Phone
    id = validators.Int()
    number = validators.String(if_missing=None)
    type = validators.PlainText(if_missing=None)
    deleted = validators.StringBool(if_missing='no')

    chained_validators = [
        validators.RequireIfPresent('number', present='type'),
        validators.RequireIfPresent('type', present='number')
    ]


class ContactSchema(DefaultSchema):
    model = models.ContactPerson
    id = validators.Int()
    title = validators.String()
    name = validators.String(not_empty=True)
    birth_date = validators.DateConverter()
    position = validators.String()
    department = validators.String()
    phone = validators.String()
    email = validators.Email()
    deleted = validators.StringBool(if_missing='no')


class CompanyMiscSchema(DefaultSchema):
    model = models.CompanyMisc
    id = validators.Int()
    name = validators.String(not_empty=True)
    description = validators.String(not_empty=True)
    deleted = validators.StringBool(if_missing='no')


class CompanyTypeSchema(DefaultSchema):
    model = models.CompanyType
    type_id = validators.String()
    deleted = validators.StringBool(if_missing='no')


class CompanySchema(DefaultSchema):
    id = validators.Int()
    name = validators.UnicodeString(not_empty=True)
    status = validators.PlainText(not_empty=True)
    website = validators.URL()
    addresses = formencode.ForEach(AddressSchema)
    phone_numbers = formencode.ForEach(PhoneSchema)
    contact_persons = formencode.ForEach(ContactSchema)
    company_types = formencode.ForEach(CompanyTypeSchema)
    company_miscs = formencode.ForEach(CompanyMiscSchema)


class DepartmentSchema(DefaultSchema):
    model = models.Department

    id = validators.String(not_empty=True)
    name = validators.String(not_empty=True)


class Username(validators.Regex):
    regex = r"^[\w!#$%&'*+\-/=?^`{|}~.]+$"
    messages = {
        'invalid': 'Invalid username'
    }


class UniqueUsername(validators.FormValidator):
    messages = {
        'taken': 'Username is already taken.'
    }

    username = None
    userid = None

    __unpackargs__ = ('username', )

    def _validate_python(self, value_dict, state):
        username = value_dict.get(self.username)
        userid = value_dict.get(self.userid)

        user = models.User.find(username=username)
        if user and user.id != userid:
            raise Invalid(
                self.message('taken', state), username, state)


class RoleSchema(DefaultSchema):
    model = models.Department
    id = validators.String()
    deleted = validators.StringBool(if_missing='no')


class AccountSchema(DefaultSchema):
    model = models.User
    id = validators.UnicodeString(if_empty=None)
    username = Username()
    password = validators.String(not_empty=True)
    departments = formencode.ForEach(RoleSchema)

    chained_validators = [
        UniqueUsername('username', userid='id'),
        validators.RequireIfPresent('username', present='password'),
        validators.RequireIfPresent('password', present='username')
    ]


class EmployeeSchema(DefaultSchema):
    model = models.Employee
    id = validators.Int()
    first_name = validators.String(not_empty=True)
    last_name = validators.String(not_empty=True)
    middle_name = validators.String()
    suffix = validators.String()
    gender = validators.String()
    birth_date = validators.DateConverter()
    civil_status = validators.String()
    position = validators.String()
    status = validators.String(not_empty=True)
    addresses = formencode.ForEach(AddressSchema)
    phone_numbers = formencode.ForEach(PhoneSchema)
    login = AccountSchema(if_missing=None)
