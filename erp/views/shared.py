from pyramid.view import view_config
from .base import BaseView


class Shared(BaseView):

    @view_config(route_name='home', renderer='erp:templates/index.pt')
    def index(self):
        return {
            'title': 'Welcome',
        }
