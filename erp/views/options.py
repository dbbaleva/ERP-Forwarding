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
    User,
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
from ..renderers import (
    Form,
    decode_request_data
)
from sqlalchemy import func
from pyramid.response import Response


class Companies(GridView, FormView):
    def index(self):
        if 'application/json' in self.request.accept.header_value:
            grid_data = self.grid_data()['current_page']
            return Response(json=grid_data.to_json(dict(id='id', text='name')))

        return self.grid_index({
            'title': 'Companies',
            'description': 'create/edit companies',
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
        return self.form_index({
            'title': 'New Company',
            'description': 'register new company'
        })

    def update(self):
        return self.form_index({
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

    def status_update(self):
        data = decode_request_data(self.request)
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            companies = Company.filter(Company.id.in_(ids))
            for company in companies:
                company.status = status

        return self.grid()

    def type_update(self):
        data = decode_request_data(self.request)
        ids = data.get('id')
        type_id = data.get('new-type')
        if ids and type:
            companies = Company.filter(Company.id.in_(ids))
            for company in companies:
                if not company.has_type(type_id):
                    company.company_types.append(CompanyType(type_id=type_id))

        return self.grid()

    @classmethod
    def views(cls, config, permission='admin'):
        super().views(config, permission)
        cls.register_view(config,
                          route_name='action',
                          attr='address_row',
                          renderer='address_row.pt',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='phone_row',
                          renderer='phone_row.pt',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='company_type',
                          renderer='company_type.pt',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='contact',
                          renderer='contact_row.pt',
                          action='contact_row',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='contact',
                          renderer='contact_edit.pt',
                          action='contact_edit',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='misc',
                          renderer='misc_row.pt',
                          action='misc_row',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='misc',
                          renderer='misc_edit.pt',
                          action='misc_edit',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='status_update',
                          request_method='POST',
                          permission=permission)
        cls.register_view(config,
                          route_name='action',
                          attr='type_update',
                          request_method='POST',
                          permission=permission)


class Accounts(GridView, FormView):
    use_global_form_template = False

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

    def form(self, values=None):
        """
        Handles form create/update methods
        """
        form = self.form_wrapper()

        if 'submit' in self.request.POST and form.validate():
            form.save_data()

        return Response(self.form_view(form))

    def form_wrapper(self):
        account_id = self.request.matchdict.get('id') or \
                     self.request.POST.get('id')

        account = Account.find(id=account_id) or Account()

        return Form(self.request, AccountSchema, account)

    @classmethod
    def views(cls, config, permission=None):
        if len(User.query().all()) > 0:
            permission = 'admin'
        super().views(config, permission)


