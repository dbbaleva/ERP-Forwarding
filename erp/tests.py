import unittest
from pyramid import testing


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

