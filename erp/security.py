from .models import User
from pyramid.security import unauthenticated_userid


def auth_callback(username, request):
    user = request.authenticated_user
    if user:
        return ['d:%s' % d.lower() for d in user.departments]


def get_authenticated_user(request):
    username = unauthenticated_userid(request)
    if username:
        return User.find(username)
    else:
        return 'Guest'


def get_csrf(request):
    token = request.session.get_csrf_token()
    if token is None:
        token = request.session.new_csrf_token()
    return token
