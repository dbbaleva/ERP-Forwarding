import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models import (
    DBSession,
    Base,
    Department,
    Employee,
    User
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)

    if 'init' in options:
        with transaction.manager:
            if 'departments' in options['init']:
                initialize_departments()
            if 'admin' in options['init']:
                initialize_admin()


def initialize_departments():
    DBSession.add_all([
        Department(id='ADM', name='HR/Admin'),
        Department(id='AFT', name='Airfreight'),
        Department(id='ATG', name='Accounting'),
        Department(id='BRK', name='Brokerage'),
        Department(id='CSD', name='Customer Service'),
        Department(id='DOM', name='Domestic'),
        Department(id='EXP', name='Export'),
        Department(id='IMP', name='Import'),
        Department(id='ITD', name='Information Technology'),
        Department(id='MKG', name='Sales/Marketing'),
        Department(id='MOV', name='Moving'),
        Department(id='TOP', name='Top Management'),
        Department(id='TRK', name='Trucking'),
    ])


def initialize_admin():
    from datetime import datetime
    from ..models import generate_uid

    user = User(
        id=generate_uid(),
        username='david',
        password='fpsmnl',
        departments=['ITD']
    )

    employee = Employee(
        first_name='David',
        last_name='Baleva',
        status='Active',
        login=user,
        created_by=user.id,
        updated_by=user.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    DBSession.add_all([user, employee])
