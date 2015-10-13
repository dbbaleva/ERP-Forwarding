from .base import (
    GridView,
    FormView,
)
from ..models import (
    Company,
    CompanyType,
    Address,
    Phone,
)
from ..schemas import (
    CompanySchema,
    AddressSchema,
    CompanyTypeSchema,
    ContactSchema,
    CompanyMiscSchema,
    PhoneSchema,
)
from ..renderers import Form
from sqlalchemy import func


class Companies(GridView, FormView):
    def index(self):
        return self.index_view({
            'title': 'Companies',
            'description': 'create/edit companies',
        })

    def grid_data(self):
        query = Company.query()
        query.page_index = int(self.request.params.get('page') or 1)

        search_params = self.request.POST
        company_type = search_params.get('type')
        status = search_params.get('status')
        kw = search_params.get('keyword')

        if company_type:
            query = query.filter(
                Company.company_types.any(func.lower(CompanyType.type_id) == func.lower(company_type)))
        if status:
            query = query.filter(Company.status == status)
        if kw:
            query = query.filter(Company.name.startswith(kw))

        return {
            'current_page': query.order_by(
                # Company.created_at.desc(),
                Company.name
            )
        }

    def create(self):
        return self.form({
            'title': 'New Company',
            'description': 'register new company'
        })

    def update(self):
        return self.form({
            'title': 'Update Company',
            'description': 'update company registration'
        })

    def form_wrapper(self):
        company_id = self.request.matchdict.get('id') or \
                     self.request.POST.get('id')

        if company_id:
            company = Company.find(id=company_id)
        else:
            company = Company(status='Active')

        return Form(self.request, CompanySchema, company)

    def address_row(self):
        return self.sub_form(Address(type='Office'), AddressSchema)

    def phone_row(self):
        return self.sub_form(Phone(type='Office'), PhoneSchema)

    def company_type(self):
        type_id = self.request.params.get('id')
        company_type = CompanyType(type_id=type_id)
        return self.sub_form(company_type, CompanyTypeSchema)

    def contact(self):
        return self.form_grid(ContactSchema, 'contact')

    def misc(self):
        return self.form_grid(CompanyMiscSchema, 'misc')

    @classmethod
    def views(cls, config):
        super().views(config)
        cls.register_view(config, route_name='action', attr='address_row', renderer='address_row.pt')
        cls.register_view(config, route_name='action', attr='phone_row', renderer='phone_row.pt')
        cls.register_view(config, route_name='action', attr='company_type', renderer='company_type.pt')
        cls.register_view(config, route_name='action', attr='contact', renderer='contact_row.pt',
                          action='contact_row')
        cls.register_view(config, route_name='action', attr='contact', renderer='contact_edit.pt',
                          action='contact_edit')
        cls.register_view(config, route_name='action', attr='misc', renderer='misc_row.pt',
                          action='misc_row')
        cls.register_view(config, route_name='action', attr='misc', renderer='misc_edit.pt',
                          action='misc_edit')

