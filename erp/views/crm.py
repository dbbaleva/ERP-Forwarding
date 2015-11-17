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
    Company,
    ContactPerson,
    Employee,
    Interaction,
    Quotation,
    QuotationRequirement,
    User,
)
from ..schemas import (
    InteractionSchema,
    QuotationSchema,
    QuotationRequirementSchema,
    QuotationCostingSchema
)
from ..renderers import (
    Form,
    FormRenderer
)


class Interactions(GridView, FormView):
    # permissions for (/crm/interactions)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, Authenticated, 'EDIT'),
    ]
    __model__ = Interaction

    def index(self):
        return self.grid_index({
            'title': 'Interactions',
            'description': 'record/update interactions'
        })

    def grid_data(self):
        # if user is an administrator:
        # query all the interactions
        query = self.query_model(with_permissions=True).filter(
            Interaction.status != 'Deleted')

        search_params = self.request.POST
        status = search_params.get('status')
        type_ = search_params.get('type')
        kw = search_params.get('keyword')

        if status:
            query = query.filter_by(status=status)
        if type_:
            query = query.filter_by(category=type_)
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
        data = self.decode_request()
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            interactions = Interaction.filter(Interaction.id.in_(ids))
            for interaction in interactions:
                interaction.status = status
                interaction.audit(self.request)

        return self.grid()

    def category_update(self):
        data = self.decode_request()
        ids = data.get('id')
        category = data.get('new-category')
        if ids and category:
            interactions = Interaction.filter(Interaction.id.in_(ids))
            for interaction in interactions:
                interaction.category = category
                interaction.audit(self.request)

        return self.grid()

    def print(self):
        data = self.decode_request()
        ids = data.get('id')

        if ids:
            interactions = self.query_model(with_permissions=True)\
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
    ]
    __model__ = Quotation

    def index(self):
        return self.grid_index({
            'title': 'Quotations',
            'description': 'create/update quotations'
        })

    def grid_data(self):
        query = self.query_model(with_permissions=True).filter(
            Quotation.status != 'Deleted')

        search_params = self.request.POST
        status = search_params.get('status')
        class_ = search_params.get('class')
        kw = search_params.get('keyword')

        if status:
            query = query.filter(status=status)
        if class_:
            query = query.filter(classification=class_)
        if kw:
            query = query.join(Company, Quotation.company_id == Company.id)\
                .join(QuotationRequirement, Quotation.id == QuotationRequirement.quotation_id)\
                .filter(or_(
                    Quotation.number.contains(kw),
                    Company.name.contains(kw),
                    QuotationRequirement.service_desc.contains(kw)
                ))

        values = self.shared_values({
            'current_page': query.order_by(
                Quotation.date.desc(),
                Quotation.number.desc(),
                Quotation.revision.desc(),
                Quotation.updated_at.desc()
            )
        })
        requirements = self.shared_requirement_values()
        service_modes = dict([(v, k) for k, v in requirements['service_modes']])
        service_types = dict([(v, k) for k, v in requirements['service_types']])
        values.update({
            'service_modes': service_modes,
            'service_types': service_types
        })
        return values

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
        employee = user.profile
        officers = Employee.query()\
            .join(User, Employee.user_id == User.id)\
            .filter(
                Employee.id != employee.id,
                User.role.in_(['Supervisor', 'Manager', 'Director'])
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

    def requirements(self):
        values = self.form_grid(QuotationRequirementSchema, 'requirement')
        values.update(self.shared_requirement_values())

        return values

    def costings(self):
        values = self.form_grid(QuotationCostingSchema, 'costing')
        root = parse_xml('crm.xml')
        groups = sorted([i.get('text') for i in root.findall('./quotation/costgroups/*')])
        units = sorted([i.get('text') for i in root.findall('./quotation/units/*')])
        currencies = sorted([i.get('code') for i in parse_xml('currencies.xml').findall('.//*')])
        values.update({
            'groups': groups,
            'units': units,
            'currencies': currencies,
        })
        return values

    def status_update(self):
        data = self.decode_request()
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            quotations = Quotation.filter(Quotation.id.in_(ids))
            for quotation in quotations:
                quotation.status = status
                quotation.audit(self.request)

        return self.grid()

    def class_update(self):
        data = self.decode_request()
        ids = data.get('id')
        class_ = data.get('new-class')
        if ids and class_:
            quotations = Quotation.filter(Quotation.id.in_(ids))
            for quotation in quotations:
                quotation.classification = class_
                quotation.audit(self.request)

        return self.grid()

    def print(self):
        data = self.decode_request()
        ids = data.get('id')

        if ids:
            quotations = self.query_model(with_permissions=True)\
                .join(Account, Quotation.account_id == Account.id)\
                .filter(Quotation.id.in_(ids))\
                .order_by(
                    Account.name
                )

            html = render('erp:templates/crm/quotations/print.pt', {
                'quotations': quotations
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
    def shared_requirement_values():
        root = parse_xml('crm.xml')

        service_types = sorted([(i.get('text'), i.get('code')) for i in root.findall('./quotation/service_types/*')])
        service_modes = sorted([(i.get('text'), i.get('code')) for i in root.findall('./quotation/service_modes/*')])
        other_services = sorted([(i.get('text'), i.get('code')) for i in root.findall('./quotation/other_services/*')])

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
                          attr='contacts',
                          renderer='contacts.pt')
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
        cls.register_view(config,
                          route_name='action',
                          attr='costings',
                          renderer='costings_row.pt',
                          action='costings_row')
        cls.register_view(config,
                          route_name='action',
                          attr='costings',
                          renderer='costings_edit.pt',
                          action='costings_edit')
        cls.register_view(config,
                          route_name='action',
                          attr='status_update',
                          request_method='POST',
                          permission='EDIT')
        cls.register_view(config,
                          route_name='action',
                          attr='class_update',
                          request_method='POST',
                          permission='EDIT')
        cls.register_view(config,
                          route_name='action',
                          attr='print',
                          request_method='POST',
                          permission='VIEW')
