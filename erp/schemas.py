import formencode
from formencode import validators
from .validators import *

from erp import models


class DefaultSchema(formencode.Schema):
    """Default schema that allows and filters extra fields"""
    allow_extra_fields = True
    filter_extra_fields = True


class LoginSchema(DefaultSchema):
    username = String(not_empty=True)
    password = String(not_empty=True)


class AddressSchema(DefaultSchema):
    model = models.Address
    id = validators.Int(if_missing=None)
    description = String(if_missing=None)
    type = validators.PlainText(if_missing=None)
    deleted = validators.StringBool(if_missing='no')

    chained_validators = [
        validators.RequireIfPresent('description', present='type'),
        validators.RequireIfPresent('type', present='description')
    ]


class PhoneSchema(DefaultSchema):
    model = models.Phone
    id = validators.Int(if_missing=None)
    number = String(if_missing=None)
    type = validators.PlainText(if_missing=None)
    deleted = validators.StringBool(if_missing='no')

    chained_validators = [
        validators.RequireIfPresent('number', present='type'),
        validators.RequireIfPresent('type', present='number')
    ]


class ContactSchema(DefaultSchema):
    model = models.ContactPerson
    id = validators.Int(if_missing=None)
    title = String()
    name = String(not_empty=True)
    birth_date = DateConverter()
    position = String()
    department = String()
    phone = String()
    email = validators.Email()
    deleted = validators.StringBool(if_missing='no')


class CompanyMiscSchema(DefaultSchema):
    model = models.CompanyMisc
    id = validators.Int(if_missing=None)
    name = String(not_empty=True)
    description = String(not_empty=True)
    deleted = validators.StringBool(if_missing='no')


class CompanyTypeSchema(DefaultSchema):
    model = models.CompanyType
    type_id = String()
    deleted = validators.StringBool(if_missing='no')


class CompanySchema(DefaultSchema):
    id = validators.Int(if_missing=None)
    name = String(not_empty=True)
    website = validators.URL()
    account_id = String()
    status = validators.PlainText(not_empty=True)
    addresses = formencode.ForEach(AddressSchema)
    phone_numbers = formencode.ForEach(PhoneSchema)
    contact_persons = formencode.ForEach(ContactSchema)
    company_types = formencode.ForEach(CompanyTypeSchema)
    company_miscs = formencode.ForEach(CompanyMiscSchema)


class DepartmentSchema(DefaultSchema):
    model = models.Department

    id = String(not_empty=True)
    name = String(not_empty=True)


class GroupSchema(DefaultSchema):
    model = models.EmployeeGroup
    department_id = String()
    deleted = validators.StringBool(if_missing='no')


class AccountRegSchema(DefaultSchema):
    model = models.User
    id = String(if_empty=None)
    username = Username(not_empty=True)
    password = Password(if_missing=None)
    role = Role(if_missing=None)

    chained_validators = [
        UniqueUsername('username', userid='id'),
        validators.RequireIfMissing('password', missing='id')
    ]


class EmployeeSchema(DefaultSchema):
    model = models.Employee
    id = validators.Int(if_missing=None)
    first_name = String(not_empty=True)
    last_name = String(not_empty=True)
    middle_name = String()
    suffix = String()
    gender = String()
    birth_date = DateConverter()
    civil_status = String()
    position = String()
    # Staff, Supervisor, Manager, Director
    status = String(not_empty=True)
    departments = Set()
    addresses = formencode.ForEach(AddressSchema)
    phone_numbers = formencode.ForEach(PhoneSchema)
    login = AccountRegSchema(if_missing=None)


class AccountSchema(DefaultSchema):
    id = String(not_empty=True)
    name = String(not_empty=True)
    email = validators.Email()


class InteractionSchema(DefaultSchema):
    id = validators.Int(if_missing=None)
    entry_date = DateConverter(not_empty=True)
    start_date = DateTimeConverter(not_empty=True)
    end_date = DateTimeConverter(not_empty=True)
    followup_date = DateTimeConverter()
    company_id = validators.Int(not_empty=True)
    contact_id = validators.Int(not_empty=True)
    account_id = String(not_empty=True)
    subject = String(not_empty=True)
    details = HtmlFormattedString(not_empty=True)
    category = String(not_empty=True)
    status = String(not_empty=True)


class QuotationRequirementSchema(DefaultSchema):
    model = models.QuotationRequirement
    id = validators.Int(if_missing=None)
    service_desc = String(not_empty=True)
    service_mode = String(not_empty=True)
    service_type = String(not_empty=True)
    other_services = Csv(if_missing=None)
    origin = String()
    destination = String()


class QuotationCostingSchema(DefaultSchema):
    model = models.QuotationCosting
    id = validators.Int(if_missing=None)
    group = String(not_empty=True)
    description = String(not_empty=True)
    currency = String()
    rate = FormattedNumber()
    unit = String()


class QuotationSchema(DefaultSchema):
    id = validators.Int(if_missing=None)
    number = String(not_empty=True)
    date = DateConverter(not_empty=True)
    revision = validators.Int(not_empty=True)
    company_id = validators.Int(not_empty=True)
    contact_id = validators.Int(not_empty=True)
    account_id = String(not_empty=True)
    noted_by = validators.Int()
    classification = String(not_empty=True)
    credit_terms = validators.Int()
    effectivity = DateConverter(not_empty=True)
    validity = DateConverter(not_empty=True)
    remarks = HtmlFormattedString(if_missing=None)
    current = validators.StringBool(if_missing=True)
    status = String(not_empty=True)

    requirements = formencode.ForEach(QuotationRequirementSchema)
    costings = formencode.ForEach(QuotationCostingSchema)

    chained_validators = [
        AutoNumber('number', param='account_id', generator=models.Quotation.generate_refno)
    ]


class ComplaintSchema(DefaultSchema):
    id = validators.Int(if_missing=None)
    date = DateConverter(not_empty=True)
    company_id = validators.Int(not_empty=True)
    contact_id = validators.Int(not_empty=True)
    account_id = String(not_empty=True)
    details = HtmlFormattedString(not_empty=True)
    type = String(not_empty=True)
    status = String(not_empty=True)
    resolved = DateConverter()
