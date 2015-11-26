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

    def test_add_departments(self):
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
        from datetime import datetime
        from .models import (
            User,
            Employee,
            Department,
            generate_uid,
        )

        uid = generate_uid()

        with transaction.manager:
            DBSession.add_all([
                Department(
                    id='ITD',
                    name='Information Technology'),
                Employee(
                    first_name='Juan',
                    last_name='Dela Cruz',
                    departments=['ITD'],
                    status='Active',
                    login=User(
                        id=uid,
                        username='admin',
                        password='fpsmnl',
                        role='Administrator'
                    ),
                    created_by=uid,
                    updated_by=uid,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            ])

        admin = User.find(username='admin')
        self.assertIsNotNone(admin)
        self.assertIsNotNone(admin.profile)
        self.assertTrue('ITD' in admin.profile.departments)

    def test_delete_employee_department(self):
        from .models import (
            Employee,
            User
        )

        self.test_create_admin()
        admin = User.find(username='admin')
        self.assertIsNotNone(admin)
        eid = admin.profile.id

        with transaction.manager:
            employee = Employee.find(id=eid)
            employee.departments.clear()    # or employee.groups.clear()
            DBSession.add(employee)

        employee = employee.find(id=eid)
        self.assertIsNotNone(employee)
        self.assertTrue(len(employee.departments) == 0)

    def test_query_on_departments(self):
        from datetime import datetime
        from .models import (
            User,
            Employee,
            EmployeeGroup,
            Company,
            ContactPerson,
            Interaction,
            generate_uid
        )

        self.test_create_admin()
        admin = User.find(username='admin')
        self.assertIsNotNone(admin)

        with transaction.manager:
            staff = Employee(
                first_name='Juan',
                last_name='Tanga',
                status='Active',
                departments=['MKG'],
                login=User(
                    id=generate_uid(),
                    username='staff',
                    password='staff',
                    role='Staff')
            )
            supervisor = Employee(
                first_name='Juan',
                last_name='Tamad',
                status='Active',
                departments=['MKG'],
                login=User(
                    id=generate_uid(),
                    username='supervisor',
                    password='supervisor',
                    role='Supervisor')
            )
            company = Company(
                name='Famous Company',
                status='Active',
                contact_persons=[
                    ContactPerson(
                        name='Contact Person',
                        position='Director'
                    )
                ]
            )
            interaction = Interaction(
                entry_date=datetime.today(),
                start_date=datetime.now(),
                end_date=datetime.now(),
                company=company,
                contact=company.contact_persons[0],
                subject='Test',
                details='The quick brown fox',
                account_id='MGT',
                category='Telemarketing',
                status='Follow-up'
            )

            staff.audit(user=admin)
            supervisor.audit(user=admin)
            company.audit(user=admin)
            interaction.audit(user=staff.login)

            DBSession.add_all([
                staff,
                supervisor,
                company,
                interaction
            ])

        self.assertGreater(User.filter_by(role='Staff').count(), 0)
        self.assertGreater(User.filter_by(role='Supervisor').count(), 0)
        self.assertGreater(Company.query().count(), 0)
        self.assertGreater(Interaction.query().count(), 0)

        user_ee_dept = User.query()\
            .join(Employee, User.id == Employee.user_id)\
            .join(EmployeeGroup, Employee.id == EmployeeGroup.employee_id)\
            .filter(
                User.role.in_([None, 'Staff', 'Supervisor']),
                EmployeeGroup.department_id.in_(['MKG'])
        ).subquery()

        interactions = Interaction.query().join(
            user_ee_dept, Interaction.created_by == user_ee_dept.c.id)

        self.assertGreater(interactions.count(), 0)

    def test_quotation_schema(self):
        from datetime import datetime
        from erp.schemas import QuotationSchema

        schema = QuotationSchema()
        today = datetime.today().strftime('%m/%d/%Y')
        values = {
            'number': 'Autogenerated',
            'date': today,
            'revision': 0,
            'company_id': 1,
            'contact_id': 1,
            'account_id': 'JTS',
            'noted_by': 1,
            'classification': 'Old Client',
            'effectivity': today,
            'validity': today,
            'credit_terms': 0,
            'status': 'Draft',
        }

        result = schema.to_python(values)
        self.assertIsNotNone(result)
        self.assertNotEqual(result['number'], 'Autogenerated')

    def test_form(self):
        from .renderers import Form
        from .renderers import DataDict
        from .models import Company
        from .schemas import CompanySchema

        request = testing.DummyRequest()
        form = Form(request,
                    CompanySchema,
                    Company(id=1))

        self.assertIsNotNone(form)
        self.assertIsInstance(form.model, Company)
        self.assertIsInstance(form.data, DataDict)
        self.assertEqual(form.data.id, form.model.id)

    def test_form_wrapper(self):
        from pyramid.testing import testConfig

        from erp import default_routes, module_configurations
        from .views.options import Companies

        with testConfig() as config:
            config.include('pyramid_chameleon')
            config.include(default_routes)
            config.include(module_configurations)

            request = testing.DummyRequest()
            setattr(request, 'csrf', None)
            setattr(request, 'authenticated_user', None)
            setattr(request, 'quick_access', None)

            companies_view = Companies(request)
            form_wrapper = companies_view.form_wrapper()
            self.assertIsNotNone(form_wrapper)


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
        res = self.testapp.get('/login', status=403)
        self.assertTrue(b'Login' in res.body)
