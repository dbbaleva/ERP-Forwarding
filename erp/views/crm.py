from datetime import (
    datetime,
    time
)

from .base import (
    FormView,
    GridView,
)
from ..helpers import parse_xml
from ..models import Interaction
from ..schemas import InteractionSchema
from ..renderers import Form
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
        kw = search_params.get('keyword')

        if status:
            query = query.filter(Interaction.status == status)
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
                end_date=datetime.combine(today, time(now.hour + 1))
            )

        return Form(self.request, InteractionSchema, employee)

    def form_renderer(self, form):
        return self.shared_values(super().form_renderer(form))

    @staticmethod
    def shared_values(values):
        root = parse_xml('interaction.xml')
        values.update({
            'now': datetime.today(),
            'categories': root.findall('./categories/*'),
            'statuses': root.findall('./statuses/*')
        })
        return values

    @classmethod
    def views(cls, config, permission='crm'):
        super().views(config, permission)
