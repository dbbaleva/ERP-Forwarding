import unittest
import transaction

from pyramid import testing
from .models import DBSession


class UnitTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from .models import Base
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://', echo=False)
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_form_wrapper(self):
        from .renderers import DataDict
        from .views.options import Companies
        from .models import Company

        request = testing.DummyRequest()
        companies_view = Companies(request)
        form = companies_view.form_wrapper()
        self.assertIsNotNone(form)
        self.assertTrue(isinstance(form.model, Company))
        self.assertTrue(isinstance(form.data, DataDict))

    def test_add_user_role(self):
        from .models import (
            User,
            Department,
            UserDepartment
        )

        with transaction.manager:
            department = Department(id='ITD', name='Information Technology')
            user = User(username='david', password='fpsmnl')
            role = UserDepartment(department_id='ITD')
            user.roles.append(role)

            DBSession.add_all([
                department,
                user
            ])

        self.assertGreater(User.query().count(), 0)
        self.assertGreater(Department.query().count(), 0)
        self.assertGreater(UserDepartment.query().count(), 0)

    def test_add_user_department(self):
        from .models import (
            User,
            Department,
            UserDepartment
        )

        with transaction.manager:
            DBSession.add_all([
                Department(
                    id='ITD',
                    name='Information Technology'),
                User(
                    username='david',
                    password='fpsmnl',
                    departments=['ITD'])
            ])

        self.assertGreater(User.query().count(), 0)
        self.assertGreater(Department.query().count(), 0)
        self.assertGreater(UserDepartment.query().count(), 0)

    def test_delete_user_roles(self):
        from .models import (
            User
        )

        self.test_add_user_role()
        with transaction.manager:
            user = User.find(username='david')
            if user:
                self.assertIsNotNone(user)
                user.roles.clear()
                DBSession.add(user)

        user = User.find(username='david')
        self.assertIsNotNone(user)
        self.assertTrue(len(user.roles) == 0)

    def test_create_departments(self):
        from .models import Department
        with transaction.manager:
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
        self.assertGreater(Department.query().count(), 0)

    def test_create_admin(self):
        from .models import (
            User,
            Employee,
            generate_uid
        )

        self.test_create_departments()

        with transaction.manager:
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
            )
            employee.audit(user=user)

            DBSession.add_all([user, employee])

        user = User.find('david')

        self.assertTrue(
            user is not None and
            user.employee is not None and
            len(user.departments) > 0
        )

    def test_query_on_department_supervisor(self):
        from datetime import datetime
        from .models import (
            Employee,
            User,
            Interaction,
            Company,
            ContactPerson,
            UserDepartment,
            generate_uid
        )

        self.test_create_admin()
        admin = User.find('david')

        with transaction.manager:
            supervisor = Employee(
                first_name='Juan',
                last_name='Dela Cruz',
                status='Active',
                position='Supervisor',
                login=User(
                    id=generate_uid(),
                    username='supervisor',
                    password='supervisor',
                    departments=['MKG']
                )
            )
            supervisor.audit(user=admin)

            staff = Employee(
                first_name='Juan',
                last_name='Tamad',
                status='Active',
                position='Staff',
                login=User(
                    id=generate_uid(),
                    username='staff',
                    password='staff',
                    departments=['MKG']
                )
            )
            staff.audit(user=admin)

            company = Company(
                name='Famous Pacific Forwarding Phils., Inc.',
                status='Active',
                contact_persons=[
                    ContactPerson(
                        name='Marina Rollan',
                    )
                ]
            )
            company.audit(user=admin)

            staff_interaction = Interaction(
                entry_date=datetime.today(),
                start_date=datetime.now(),
                end_date=datetime.now(),
                company=company,
                contact=company.contact_persons[0],
                subject='Test',
                details='The quick brown fox',
                account_code='MGT',
                category='Telemarketing',
                status='Follow-up'
            )
            staff_interaction.audit(user=staff.login)

            DBSession.add_all([
                supervisor,
                staff,
                company,
                staff_interaction
            ])

        self.assertGreater(Employee.filter_by(position='Staff').count(), 0)
        self.assertGreater(Employee.filter_by(position='Supervisor').count(), 0)
        self.assertGreater(Company.query().count(), 0)
        self.assertGreater(Interaction.query().count(), 0)

        user_dept = User.query()\
            .join(Employee, User.id == Employee.user_id)\
            .join(UserDepartment)\
            .filter(
                Employee.position.in_([None, 'Staff', 'Supervisor']),
                UserDepartment.department_id.in_(['MKG'])
        ).subquery()

        interactions = Interaction.query().join(
            user_dept, Interaction.created_by == user_dept.c.id)

        self.assertGreater(interactions.count(), 0)

        # QUERY1:
        # ========
        # SELECT i1.*
        # FROM interaction AS i1 INNER JOIN
        # user AS u1 ON i1.created_by = u1.id INNER JOIN
        # employee AS ee ON u1.id = ee.user_id
        # WHERE u1.id IN (
        #     SELECT user_department.user_id
        #     FROM user_department
        #     WHERE user_department.department_id = 'MKG')
        #     AND ee.position IN ('Staff','Supervisor')
        #
        # QUERY2 (same as QUERY1):
        # ========
        # SELECT interaction.*
        # FROM interaction INNER JOIN (
        #     SELECT user_department.user_id
        #     FROM user_department
        #     WHERE user_department.department_id = 'MKG'
        #     ) AS anon_1 ON interaction.created_by = anon_1.user_id INNER JOIN
        # employee ON anon_1.user_id = employee.user_id
        # WHERE employee.position IN ('Staff', 'Supervisor')


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        from . import main
        from pyramid.paster import get_appsettings
        config_uri = 'development.ini'
        settings = get_appsettings(config_uri)
        app = main({}, **settings)
        from webtest import TestApp
        self.testapp = TestApp(app)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_get_login(self):
        res = self.testapp.get('/', status=200)
        self.assertTrue(b'Login' in res.body)
