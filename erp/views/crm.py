import io
from datetime import (
    datetime,
    timedelta,
    time
)
from pyramid.httpexceptions import HTTPNoContent
from pyramid.renderers import render
from pyramid.response import Response
from pyramid.security import (
    Authenticated,
    ALL_PERMISSIONS,
    Allow,
)
from sqlalchemy import or_
from xhtml2pdf import pisa
from .base import (
    FormView,
    GridView,
)
from ..helpers import parse_xml
from ..models import (
    Account,
    ContactPerson,
    Employee,
    Interaction,
    Quotation,
    QuotationCosting,
    QuotationRequirement,
    User,
    UserDepartment
)
from ..schemas import (
    InteractionSchema,
    QuotationSchema,
    QuotationRequirementSchema,
)
from ..renderers import (
    Form,
    FormRenderer,
    decode_request_data
)


class Interactions(GridView, FormView):
    # permissions for (/crm/interactions)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, Authenticated, 'EDIT'),
        (Allow, 'D:ITD', ALL_PERMISSIONS),
    ]
    __model__ = Interaction

    def index(self):
        return self.grid_index({
            'title': 'Interactions',
            'description': 'record/update interactions'
        })

    def grid_data(self):
        user = self.request.authenticated_user
        employee = user.employee
        departments = list(user.departments)

        # if user is an administrator:
        # query all the interactions
        if self.request.has_permission(ALL_PERMISSIONS):
            query = Interaction.query()

        # if user is supervisor:
        # then query all of it's staff interactions
        elif employee.position == 'Supervisor':
            user_dept = User.query()\
                .join(Employee, User.id == Employee.user_id)\
                .join(UserDepartment)\
                .filter(
                    Employee.position.in_([None, 'Staff', 'Supervisor']),
                    UserDepartment.department_id.in_(departments)
            ).subquery()

            query = Interaction.query().join(
                user_dept, Interaction.created_by == user_dept.c.id)

        # if user is manager
        # query all interactions from the department
        elif employee.position == 'Manager':
            user_dept = User.query()\
                .join(UserDepartment)\
                .filter(
                    UserDepartment.department_id.in_(departments)
            ).subquery()

            query = Interaction.query().join(
                user_dept, Interaction.created_by == user_dept.c.id)

        # query the user's interactions
        else:
            query = Interaction.query().filter(
                Interaction.created_by == user.id
            )

        query.page_index = int(self.request.params.get('page') or 1)

        search_params = self.request.POST
        status = search_params.get('status')
        type = search_params.get('type')
        kw = search_params.get('keyword')

        if status:
            query = query.filter(Interaction.status == status)
        if type:
            query = query.filter(Interaction.category == type)
        if kw:
            query = query.filter(or_(
                Interaction.subject.contains(kw),
                Interaction.details.contains(kw)
            ))

        return self.shared_values({
            'current_page': query.order_by(
                Interaction.entry_date.desc(),
                Interaction.updated_at.desc()
            )
        })

    def create(self):
        return self.form_index({
            'title': 'New Interaction',
            'description': 'record new interaction'
        })

    def update(self):
        return self.form_index({
            'title': 'Update Interaction',
            'description': 'edit/update interaction',
        })

    def form_wrapper(self):
        interaction = self.request.context
        if interaction is None or not isinstance(interaction, Interaction):
            today = datetime.today().date()
            now = datetime.now().time()
            interaction = Interaction(
                entry_date=today,
                start_date=datetime.combine(today, time(now.hour)),
                end_date=datetime.combine(today, time(now.hour + 1)),
                details=''
            )

        return Form(self.request, InteractionSchema, interaction)

    def form_renderer(self, form):
        values = super().form_renderer(form)
        values = self.shared_values(values)

        company_options = []
        company = form.model.company
        if company:
            company_options = FormRenderer.options([(company.name, company.id), ])

        contact_options = []
        contact = form.model.contact
        if contact:
            contact_options = FormRenderer.options([(contact.name, contact.id), ])

        values.update({
            'company_options': company_options,
            'contact_options': contact_options
        })

        return values

    def contacts(self):
        company_id = self.request.params.get('id')
        contacts = ContactPerson.filter(
            ContactPerson.id == company_id).all()

        contact_options = []
        form = FormRenderer()
        if len(contacts) > 0:
            contact_options = form.options([(c.name, c.id) for c in contacts])
        return {
            'form': form,
            'contact_options': contact_options
        }

    def status_update(self):
        data = decode_request_data(self.request)
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            interactions = Interaction.filter(Interaction.id.in_(ids))
            for interaction in interactions:
                interaction.status = status
                interaction.audit(self.request)

        return self.grid()

    def category_update(self):
        data = decode_request_data(self.request)
        ids = data.get('id')
        category = data.get('new-category')
        if ids and category:
            interactions = Interaction.filter(Interaction.id.in_(ids))
            for interaction in interactions:
                interaction.category = category
                interaction.audit(self.request)

        return self.grid()

    def print(self):
        data = decode_request_data(self.request)
        ids = data.get('id')

        if ids:
            interactions = Interaction.query()\
                .join(Account, Interaction.account_id == Account.id)\
                .filter(Interaction.id.in_(ids))\
                .order_by(
                    Account.name
                )
            html = render('erp:templates/crm/interactions/summary.pt', {
                'interactions': interactions
            }, self.request)
            with io.StringIO() as pdf:
                doc = pisa.CreatePDF(html, pdf)
                if not doc.err:
                    pdf.seek(0)
                    return Response(
                        body=pdf.read(),
                        charset='latin1',
                        content_type='application/pdf')

        return HTTPNoContent()

    @staticmethod
    def shared_values(values):
        root = parse_xml('crm.xml')
        statuses = [(i.get('text'), i.get('color')) for i in root.findall('./interaction/statuses/*')]
        categories = [(i.get('text'), i.get('icon')) for i in root.findall('./interaction/categories/*')]
        values.update({
            'now': datetime.today().date(),
            'categories': categories,
            'statuses': statuses,
            'accounts': Account.query().order_by(Account.name).all()
        })
        return values

    @classmethod
    def add_views(cls, config):
        super().add_views(config)

        cls.register_view(config,
                          route_name='action',
                          attr='contacts',
                          renderer='contacts.pt')
        cls.register_view(config,
                          route_name='action',
                          attr='status_update',
                          request_method='POST',
                          permission='EDIT')
        cls.register_view(config,
                          route_name='action',
                          attr='category_update',
                          request_method='POST',
                          permission='EDIT')
        cls.register_view(config,
                          route_name='action',
                          attr='print',
                          request_method='POST',
                          permission='VIEW')


class Quotations(GridView, FormView):
    # permissions for (/crm/quotations)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, Authenticated, 'EDIT'),
        (Allow, 'D:ITD', ALL_PERMISSIONS),
    ]
    __model__ = Quotation

    def index(self):
        return self.grid_index({
            'title': 'Quotations',
            'description': 'create/update quotations'
        })

    def grid_data(self):
        query = Quotation.query()

        return self.shared_values({
            'current_page': query.order_by(
                Quotation.date.desc(),
                Quotation.updated_at.desc()
            )
        })

    def create(self):
        return self.form_index({
            'title': 'New Quotation',
            'description': 'create new quotation'
        })

    def update(self):
        return self.form_index({
            'title': 'Update Quotation',
            'description': 'edit/revise quotation',
        })

    def form_wrapper(self):
        quotation = self.request.context
        if quotation is None or not isinstance(quotation, Quotation):
            today = datetime.today().date()
            quotation = Quotation(
                date=today,
                number='Autogenerated',
                revision=0,
                remarks='',
                effectivity=today,
                validity=today+timedelta(days=30),
                credit_terms=0,
                status='Draft'
            )

        return Form(self.request, QuotationSchema, quotation)

    def form_renderer(self, form):
        values = super().form_renderer(form)
        values = self.shared_values(values)

        company_options = []
        company = form.model.company
        if company:
            company_options = FormRenderer.options([(company.name, company.id), ])

        contact_options = []
        contact = form.model.contact
        if contact:
            contact_options = FormRenderer.options([(contact.name, contact.id), ])

        user = self.request.authenticated_user
        employee = user.employee

        officers = Employee.filter(
            Employee.id != employee.id,
            Employee.position.in_(['Supervisor', 'Manager', 'Director'])
        ).order_by(
            Employee.first_name,
            Employee.last_name
        ).all()

        noted_options = FormRenderer.options([(ee.fullname, ee.id) for ee in officers])

        values.update({
            'company_options': company_options,
            'contact_options': contact_options,
            'noted_options': noted_options
        })
        values.update(self.shared_requirement_values())

        return values

    def requirements(self):
        values = self.form_grid(QuotationRequirementSchema, 'requirement')
        values.update(self.shared_requirement_values())

        return values

    @staticmethod
    def shared_requirement_values():
        root = parse_xml('crm.xml')

        service_types = [(i.get('text'), i.get('code')) for i in root.findall('./quotation/service_types/*')]
        service_modes = [(i.get('text'), i.get('code')) for i in root.findall('./quotation/service_modes/*')]
        other_services = [(i.get('text'), i.get('code')) for i in root.findall('./quotation/other_services/*')]

        return {
            'service_types': service_types,
            'service_modes': service_modes,
            'other_services': other_services
        }

    @staticmethod
    def shared_values(values):
        root = parse_xml('crm.xml')
        statuses = [(i.get('text'), i.get('color')) for i in root.findall('./quotation/statuses/*')]
        classifications = [(i.get('text'), i.get('icon')) for i in root.findall('./quotation/classifications/*')]
        values.update({
            'now': datetime.today().date(),
            'classifications': classifications,
            'statuses': statuses,
            'accounts': Account.query().order_by(Account.name).all()
        })
        return values

    @classmethod
    def add_views(cls, config):
        super().add_views(config)
        cls.register_view(config,
                          route_name='action',
                          attr='requirements',
                          renderer='requirements_row.pt',
                          action='requirements_row')
        cls.register_view(config,
                          route_name='action',
                          attr='requirements',
                          renderer='requirements_edit.pt',
                          action='requirements_edit')
