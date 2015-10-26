import formencode
from formencode import validators
from .validators import *

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


class RoleSchema(DefaultSchema):
    model = models.UserDepartment
    department_id = validators.String()
    deleted = validators.StringBool(if_missing='no')


class AccountRegSchema(DefaultSchema):
    model = models.User
    id = validators.UnicodeString(if_empty=None)
    username = Username(not_empty=True)
    password = Password(if_missing=None)
    roles = formencode.ForEach(RoleSchema)

    chained_validators = [
        UniqueUsername('username', userid='id'),
        validators.RequireIfMissing('password', missing='id')
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
    # Staff, Supervisor, Manager, Director
    position = validators.String()
    status = validators.String(not_empty=True)
    addresses = formencode.ForEach(AddressSchema)
    phone_numbers = formencode.ForEach(PhoneSchema)
    login = AccountRegSchema(if_missing=None)


class AccountSchema(DefaultSchema):
    id = validators.String(not_empty=True)
    name = validators.String(not_empty=True)
    email = validators.Email()


class InteractionSchema(DefaultSchema):
    id = validators.Int()
    entry_date = validators.DateConverter(not_empty=True)
    start_date = DateTimeConverter(not_empty=True)
    end_date = DateTimeConverter(not_empty=True)
    followup_date = DateTimeConverter()
    company_id = validators.Int(not_empty=True)
    contact_id = validators.Int()
    account_code = validators.String(not_empty=True)
    subject = validators.String(not_empty=True)
    details = HtmlFormattedString(not_empty=True)
    category = validators.String(not_empty=True)
    status = validators.String(not_empty=True)

