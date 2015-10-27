from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from pyramid.renderers import get_renderer
from pyramid.events import (
    subscriber,
    BeforeRender,
    NewRequest,
)


@subscriber(BeforeRender)
def add_base_template(event):
    base = get_renderer("templates/base.pt").implementation()
    event.update({'base': base})


@subscriber(NewRequest)
def csrf_validation(event):
    if event.request.environ.get("paste.testing"):
        return
    if event.request.method == "POST":
        token = event.request.POST.get("_csrf")
        if token is None or token != event.request.session.get_csrf_token():
            # Skip csrf validation for logout
            logout_url = event.request.route_url('logout')
            if event.request.url == logout_url:
                pass
            else:
                raise HTTPForbidden("CSRF token is missing or invalid")
