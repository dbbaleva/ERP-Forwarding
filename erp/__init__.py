from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPMovedPermanently
from pyramid.session import SignedCookieSessionFactory

from sqlalchemy import engine_from_config

from .helpers import (
    quick_access,
)

from .models import (
    DBSession,
    Base,
    RootFactory,
)

from .security import (
    auth_callback,
    get_authenticated_user,
    get_csrf,
)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    session_factory = SignedCookieSessionFactory(
        settings['session.secret']
    )

    authn_policy = AuthTktAuthenticationPolicy(
        settings['session.secret'],
        callback=auth_callback,
        hashalg='sha512')

    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(
        settings=settings,
        session_factory=session_factory,
        root_factory=RootFactory,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy
    )

    config.include('pyramid_chameleon')
    config.add_request_method(get_authenticated_user, 'authenticated_user', reify=True)
    config.add_request_method(get_csrf, 'csrf', reify=True)
    config.add_request_method(quick_access, 'quick_access', reify=True)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('static/lib', 'lib')
    config.add_route('login', '/')
    config.add_route('logout', '/logout')
    config.include(default_routes)
    config.include(view_configurations)
    config.scan()
    return config.make_wsgi_app()


def default_routes(config):
    configure_route(config, 'index', '/{module}/{cls}')
    configure_route(config, 'action', '/{module}/{cls}/{action}')
    configure_route(config, 'action_id', '/{module}/{cls}/{id}/{action}')


def configure_route(config, name, pattern, **kwargs):
    config.add_route(name, pattern, **kwargs)
    if not pattern.endswith('/'):
        config.add_route(name + '_auto', pattern + '/')

        def redirector(request):
            return HTTPMovedPermanently(request.route_url(name, _query=request.GET, **request.matchdict))

        config.add_view(redirector, route_name=name + '_auto')


def view_configurations(config):
    from erp.views import (
        hris,
        options,
    )
    hris.Employees.views(config)
    hris.Departments.views(config)
    options.Companies.views(config)
