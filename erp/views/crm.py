from datetime import (
    datetime,
    time
)

from .base import (
    FormView,
    GridView,
)
from ..helpers import parse_xml
from ..models import (
    Interaction,
    ContactPerson,
    Account,
)
from ..schemas import InteractionSchema
from ..renderers import (
    Form,
    FormRenderer
)
from sqlalchemy import or_


class Interactions(GridView, FormView):
    def index(self):
        return self.grid_index({
            'title': 'Interactions',
            'description': 'record/update interactions'
        })

    def grid_data(self):
        query = Interaction.query()
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
                Interaction.start_date.desc(),
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
        interaction_id = self.request.matchdict.get('id') or \
                     self.request.POST.get('id')

        if interaction_id:
            employee = Interaction.find(id=interaction_id)
        else:
            today = datetime.today().date()
            now = datetime.now().time()
            employee = Interaction(
                entry_date=today,
                start_date=datetime.combine(today, time(now.hour)),
                end_date=datetime.combine(today, time(now.hour + 1)),
                details="The quick brown fox"
            )

        return Form(self.request, InteractionSchema, employee)

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
    def views(cls, config, permission='crm'):
        super().views(config, permission)

        cls.register_view(config,
                          route_name='action',
                          attr='contacts',
                          renderer='contacts.pt',
                          permission=permission)
