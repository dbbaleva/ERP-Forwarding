from pyramid.security import (
    Authenticated,
    Allow,
)
from pyramid.response import Response
from sqlalchemy import func

from .base import (
    GridView,
    FormView,
)
from ..models import (
    Company,
    CompanyType,
    Address,
    Phone,
    Account,
)
from ..schemas import (
    CompanySchema,
    AddressSchema,
    CompanyTypeSchema,
    ContactSchema,
    CompanyMiscSchema,
    PhoneSchema,
    AccountSchema
)


class Companies(GridView, FormView):
    # permissions for (/options/companies)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
    ]
    __model__ = Company
    __schema__ = CompanySchema

    def index(self):
        if 'application/json' in self.request.accept.header_value:
            grid_data = self.grid_data()['current_page']
            return Response(json=grid_data.to_json(dict(id='id', text='name')))

        return self.grid_index({
            'title': 'Companies',
            'description': 'create/edit companies'
        })

    def grid_data(self):
        query = Company.filter(Company.status != 'Deleted')
        query.page_index = int(self.request.params.get('page') or 1)

        search_params = self.request.params
        company_type = search_params.get('type')
        status = search_params.get('status')
        kw = search_params.get('keyword')

        if company_type:
            query = query.filter(
                Company.company_types.any(func.lower(CompanyType.type_id) == func.lower(company_type))
            )
        if status:
            query = query.filter(status=status)
        if kw:
            query = query.filter(Company.name.startswith(kw))

        return {
            'current_page': query.order_by(
                # Company.created_at.desc(),
                Company.name
            )
        }

    def create(self):
        return self.form_index({
            'title': 'New Company',
            'description': 'register new company'
        })

    def update(self):
        return self.form_index({
            'title': 'Update Company',
            'description': 'update company registration'
        })

    def form_values(self, form):
        return {
            'accounts': Account.query().order_by(Account.name).all()
        }

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

    def status_update(self):
        data = self.decode_request()
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            companies = Company.filter(Company.id.in_(ids))
            for company in companies:
                company.status = status
                company.audit(self.request)

        return self.grid()

    def type_update(self):
        data = self.decode_request()
        ids = data.get('id')
        type_id = data.get('new-type')
        if ids and type:
            companies = Company.filter(Company.id.in_(ids))
            for company in companies:
                if not company.has_type(type_id):
                    company.company_types.append(CompanyType(type_id=type_id))
                    company.audit(self.request)

        return self.grid()

    @classmethod
    def add_views(cls, config):
        super().add_views(config)
        cls.register_view(config, route_name='action', attr='address_row', renderer='address_row.pt')
        cls.register_view(config, route_name='action', attr='phone_row', renderer='phone_row.pt')
        cls.register_view(config, route_name='action', attr='company_type', renderer='company_type.pt')
        cls.register_view(config, route_name='action', attr='contact', renderer='contact_row.pt', action='contact_row')
        cls.register_view(config, route_name='action', attr='contact', renderer='contact_edit.pt',
                          action='contact_edit')
        cls.register_view(config, route_name='action', attr='misc', renderer='misc_row.pt', action='misc_edit')
        cls.register_view(config, route_name='action', attr='status_update', request_method='POST', permission='EDIT')
        cls.register_view(config, route_name='action', attr='type_update', request_method='POST', permission='EDIT')


class Accounts(GridView, FormView):
    # permissions for (/options/accounts)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, 'D:ITD', 'EDIT'),
    ]
    __model__ = Account
    __schema__ = AccountSchema

    use_global_form_template = False
    use_form_macros = False

    def index(self):
        return self.grid_index({
            'title': 'Accounts',
            'description': 'create/update accounts',
        })

    def grid_data(self):
        query = Account.query()
        query.page_index = int(self.request.params.get('page') or 1)

        search_params = self.request.POST
        kw = search_params.get('keyword')

        if kw:
            query = query.filter(Account.name.startswith(kw))

        return {
            'current_page': query.order_by(
                Account.id,
                Account.name
            )
        }

    def search_box(self, template_name='erp:templates/options/accounts/search_box.pt'):
        return super().search_box(template_name)

    def delete(self):
        data = self.decode_request()
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            accounts = Account.filter(Account.id.in_(ids))
            accounts.delete(synchronize_session=False)

        return self.grid()

    @classmethod
    def add_views(cls, config):
        super().add_views(config)
        cls.register_view(config, route_name='action', attr='delete', request_method='POST', permission='EDIT')
