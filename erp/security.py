from .models import User
from pyramid.security import (
    unauthenticated_userid,
    ALL_PERMISSIONS
)


def auth_callback(username, request):
    user = request.authenticated_user
    if user:
        acl = []
        if user.profile:
            acl = ['D:%s' % d.upper() for d in user.profile.departments]
        acl.append('R:%s' % user.role.upper())
        return acl


def get_authenticated_user(request):
    username = unauthenticated_userid(request)
    if username:
        return User.find(username)


def get_csrf(request):
    token = request.session.get_csrf_token()
    if token is None:
        token = request.session.new_csrf_token()
    return token


def has_admin_permissions(request):
    return request is not None and request.has_permission(ALL_PERMISSIONS)
