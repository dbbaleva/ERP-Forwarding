from pyramid.view import (
    view_config,
    forbidden_view_config
)
from pyramid.security import (
    remember,
    forget,
)
from pyramid.httpexceptions import HTTPFound
from .base import BaseView
from ..renderers import (
    Form,
    FormRenderer
)
from ..schemas import LoginSchema
from ..models import User


class Shared(BaseView):

    @view_config(route_name='login', renderer='erp:templates/login.pt')
    @forbidden_view_config(renderer='erp:templates/login.pt')
    def login(self):
        login_url = self.request.route_url('login')
        referrer = self.request.url

        if referrer == login_url:
            referrer = self.request.route_url('index', module='options', cls='companies')

        came_from = self.request.params.get('came_from', referrer)
        form = Form(self.request, LoginSchema)

        if 'submit' in self.request.POST and form.validate():
            username, password = form.data['username'], form.data['password']
            if User.validate(username, password):
                headers = remember(self.request, username)
                return HTTPFound(location=came_from, headers=headers)
            self.request.session.flash(u'Failed to username, invalid username or password.')

        return {
            'title': 'Login',
            'form': FormRenderer(form),
            'came_from': came_from
        }

    @view_config(route_name='logout', request_method='POST')
    def logout(self):
        headers = forget(self.request)
        location = self.request.route_url('login')
        return HTTPFound(location=location, headers=headers)
