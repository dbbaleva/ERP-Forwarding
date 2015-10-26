import time
from datetime import datetime

from formencode import validators
from formencode.api import Invalid

from erp import models

__all__ = [
    'Username',
    'Password',
    'UniqueUsername',
    'DateTimeConverter',
    'HtmlFormattedString'
]


class Username(validators.Regex):
    regex = r"^[\w!#$%&'*+\-/=?^`{|}~.]+$"
    messages = {
        'invalid': 'Invalid username'
    }


class Password(validators.UnicodeString):
    def update_model_attr(self, model, key, value):
        if not value:
            return

        if model and hasattr(model, key):
            value = self.to_python(value)
            hashed_password = models.User.hash_password(value)
            setattr(model, key, hashed_password)


class UniqueUsername(validators.FormValidator):
    messages = {
        'taken': 'Username is already taken.'
    }

    username = None
    userid = None

    __unpackargs__ = ('username', )

    def _validate_python(self, value_dict, state):
        username = value_dict.get(self.username)
        userid = value_dict.get(self.userid)

        user = models.User.find(username=username)
        if user and user.id != userid:
            raise Invalid(
                self.message('taken', state), username, state)


class DateTimeConverter(validators.FancyValidator):
    format = '%m/%d/%Y %I:%M %p'

    messages = {
        'badFormat': 'Invalid datetime format',
    }

    def _convert_to_python(self, value, state):
        """Parse a string and return a datetime object."""
        if value and isinstance(value, datetime):
            return value

        else:
            try:
                format = self.format
                if callable(format):
                    format = format()
                time_tuple = time.strptime(value, format)
                return datetime(
                    year=time_tuple.tm_year,
                    month=time_tuple.tm_mon,
                    day=time_tuple.tm_mday,
                    hour=time_tuple.tm_hour,
                    minute=time_tuple.tm_min
                )
            except ValueError:
                raise Invalid(self.message('badFormat', state), value, state)

    def _convert_from_python(self, value, state):
        """Return a string representation of a datetime object."""
        if not value:
            return None
        elif isinstance(value, datetime):
            format = self.format
            if callable(format):
                format = format()
            return value.strftime(format)
        else:
            return value


class HtmlFormattedString(validators.FancyValidator):
    """
    Validates html formatted string, should raise an exception if it
    is an html string with empty data, i.e.: <p></p>
    """

    def _validate_python(self, value, state):
        from .helpers import strip_html
        value = strip_html(value)
        if not value and self.not_empty:
            raise Invalid(self.message('empty', state), value, state)
