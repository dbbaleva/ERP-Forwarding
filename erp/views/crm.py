from datetime import (
    datetime,
    time
)
from pyramid.security import (
    Authenticated,
    ALL_PERMISSIONS,
    Allow,
)

from sqlalchemy import or_

from .base import (
    FormView,
    GridView,
)
from ..helpers import parse_xml
from ..models import (
    Interaction,
    ContactPerson,
    Account,
    Employee,
    User,
    UserDepartment
)
from ..schemas import InteractionSchema
from ..renderers import (
    Form,
    FormRenderer,
    decode_request_data
)


class Interactions(GridView, FormView):
    # permissions for (/options/interactions)
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

    @staticmethod
    def shared_values(values):
        root = parse_xml('interaction.xml')
        values.update({
            'now': datetime.today().date(),
            'categories': root.findall('./categories/*'),
            'statuses': root.findall('./statuses/*'),
            'accounts': Account.query().all()
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
