from datetime import (
    datetime,
    timedelta
)

from pyramid.view import (
    view_config,
    forbidden_view_config
)
from pyramid.security import (
    remember,
    forget,
    Authenticated,
    ALL_PERMISSIONS
)
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPForbidden
)
from sqlalchemy.sql import func

from .base import BaseView
from ..renderers import (
    Form,
    FormRenderer
)
from ..schemas import LoginSchema
from ..models import (
    User,
    Interaction,
    ContactPerson
)

from ..validators import DateConverter


class Shared(BaseView):
    @view_config(route_name='login', renderer='erp:templates/login.pt')
    @forbidden_view_config(renderer='erp:templates/login.pt')
    def login(self):
        login_url = self.request.route_url('login')
        referrer = self.request.url if self.request.method == 'GET' else self.request.referrer

        if referrer == login_url:
            referrer = self.request.route_url('dashboard')

        came_from = self.request.params.get('came_from', referrer)
        form = Form(self.request, LoginSchema)

        # skip login if already authenticated and the
        # current request has the minimum required permissions
        if self.request.method == 'GET' and \
                not isinstance(self.request.exception, HTTPForbidden) and \
                Authenticated in self.request.effective_principals:
            return HTTPFound(location=came_from)

        if 'submit' in self.request.POST and form.validate():
            username, password = form.data['username'], form.data['password']
            if User.validate(username, password):
                headers = remember(self.request, username)
                return HTTPFound(location=came_from, headers=headers)
            self.request.session.flash(u'Failed to login, invalid username or password.')

        self.request.response.status = 403

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

    @view_config(route_name='dashboard', renderer='erp:templates/dashboard.pt')
    def dashboard(self):
        return {
            'title': 'Dashboard',
            'description': 'Welcome to Enterprise Resource Planning'
        }

    @view_config(route_name='events', renderer='json', permission='VIEW')
    def events(self):
        has_all_permissions = self.request.has_permission(ALL_PERMISSIONS)
        converter = DateConverter()
        start_date = converter.to_python(self.request.params.get('start')) or datetime.today().date()
        end_date = converter.to_python(self.request.params.get('end')) or datetime.today().date()

        if has_all_permissions:
            interactions = Interaction.query()
            contacts = ContactPerson.query()
        else:
            user = self.request.authenticated_user
            interactions = Interaction.query_with_permissions(user)
            contacts = ContactPerson.query_with_permissions(user)

        interactions = interactions.filter(
            func.date(Interaction.followup_date) >= start_date,
            func.date(Interaction.followup_date) <= end_date,
            Interaction.status != 'Deleted'
        )

        contacts = contacts.filter(
            func.extract('month', ContactPerson.birth_date) >= start_date.month,
            func.extract('month', ContactPerson.birth_date) <= end_date.month
        )

        return Event.to_json(interactions, contacts)


class Event(dict):
    __columns__ = [
        'id',
        'title',
        'allDay',
        'start',
        'end',
        'textColor',
        'backgroundColor'
    ]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.__columns__:
                self[key] = value

    @classmethod
    def to_json(cls, *args):
        events = []
        try:
            for items in args:
                for i in iter(items):
                    if isinstance(i, Interaction):
                        evt = cls.__interaction_to_event__(i)
                    elif isinstance(i, ContactPerson):
                        evt = cls.__contactperson_to_event(i)
                    elif isinstance(i, dict):
                        evt = cls(**i)
                    else:
                        evt = None
                    events.append(evt)
        except:
            pass

        return events

    @classmethod
    def __interaction_to_event__(cls, item):
        return cls(**dict(
            id='interaction-%d' % item.id,
            title=item.subject,
            start=item.followup_date.isoformat(),
            end=(item.followup_date + timedelta(hours=1)).isoformat()
        ))

    @classmethod
    def __contactperson_to_event(cls, item):
        return cls(**dict(
            id='contact-%d' % item.id,
            title=item.name,
            start=item.birth_date.isoformat(),
            allDay=True
        ))
