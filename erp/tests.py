import unittest
import transaction

from pyramid import testing
from .models import DBSession


class TestOptionsCompanies(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
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


class TestModels(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from .models import Base
        from sqlalchemy import create_engine
        engine = create_engine(
            'sqlite://'
            # , echo=True
        )
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

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

        self.assertGreater(len(User.query().all()), 0)
        self.assertGreater(len(Department.query().all()), 0)
        self.assertGreater(len(UserDepartment.query().all()), 0)

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
