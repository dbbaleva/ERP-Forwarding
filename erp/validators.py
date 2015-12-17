import re
import time
from datetime import datetime

from formencode import validators
from formencode.api import Invalid

from erp import models

__all__ = [
    'Username',
    'Password',
    'Role',
    'UniqueUsername',
    'DateConverter',
    'DateTimeConverter',
    'HtmlFormattedString',
    'AutoNumber',
    'Csv',
    'Set',
    'FormattedNumber',
    'String'
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


class Role(validators.String):
    def update_model_attr(self, model, key, value):
        if not value:
            return

        if model and hasattr(model, key):
            setattr(model, key, self.to_python(value))


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


class DateConverter(validators.FancyValidator):
    _month_names = {
        'jan': 1, 'january': 1,
        'feb': 2, 'febuary': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
        }
        
    _date_re = [
        (
            re.compile(
                r'^\s*(\d\d?)[\-\./\\](\d\d?|%s)[\-\./\\](\d\d\d?\d?)\s*$'
                    % '|'.join(_month_names), re.I),
            lambda groups: (int(groups[2]), int(groups[0]), int(groups[1]))
        ),
        (
            re.compile(
                r'^\s*(\d\d?|%s)[\-\./\\](\d\d?)[\-\./\\](\d\d\d?\d?)\s*$'
                    % '|'.join(_month_names), re.I),
            lambda groups: (int(groups[2]), int(groups[1]), int(groups[0]))
        ),
        (
            re.compile(
                r'^\s*(\d\d\d?\d?)[\-\./\\](\d\d?|%s)[\-\./\\](\d\d?)\s*$'
                    % '|'.join(_month_names), re.I),
            lambda groups: (int(groups[0]), int(groups[1]), int(groups[2]))
        )
    ]

    messages = {
        'badFormat': 'Invalid datetime format',
    }

    def _convert_to_python(self, value, state):
        """Parse a string and return a date object"""
        try:
            return self._string_to_date(value, state)
        except ValueError as ex:
            raise Invalid(self.message('badFormat', state), value, state)

    def _string_to_date(self, value, state):
        for expr, formatter in self._date_re:
            match = expr.search(value)
            if match:
                date_tpl = formatter(match.groups())
                return datetime(*date_tpl).date()

        raise Invalid(self.message('badFormat', state), value, state)

    def _convert_from_python(self, value, state):
        """Returns a string representation of a date object."""
        if isinstance(value, str):
            value = self._string_to_date(value, state)
        return value.strftime('%m/%d/%Y')


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


class AutoNumber(validators.FormValidator):
    messages = {
        'badFormat': 'Invalid format',
    }

    number = None
    generator = None
    param = None

    __unpackargs__ = ('number', )

    def _convert_to_python(self, value_dict, state):
        """Parse a string and return an autogenerated number object."""
        value = value_dict.get(self.number)
        param = value_dict.get(self.param)
        generator = self.generator

        if (value is None or value.lower() == 'autogenerated') \
                and generator is not None \
                and callable(generator):
            try:
                value = generator(param)
                value_dict.update({
                    self.number: value
                })
            except ValueError:
                raise Invalid(self.message('badFormat', state), value, state)

        return value_dict


class Csv(validators.FancyValidator):
    """
    Comma separated values
    """

    accept_iterator = True
    separator = ','

    def _convert_to_python(self, value, state):
        if isinstance(value, list):
            value = self.separator.join(value)
        return value.rstrip(',')

    def _convert_from_python(self, value, state):
        if not value:
            value = []
        elif isinstance(value, str):
            value = value.split(self.separator)
        return value


class Set(validators.Set):
    """
    List of values
    """
    accept_iterator = True

    def _convert_from_python(self, value, state):
        return tuple(value or [])


class FormattedNumber(validators.Number):
    number_format = '{:0,.2f}'

    def _convert_from_python(self, value, state):
        """Return a formatted string representation of a number."""
        if isinstance(value, str):
            value = float(value)
        return self.number_format.format(value)


class String(validators.String):
    inputEncoding = None
    outputEncoding = None
