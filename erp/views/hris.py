from pyramid.security import (
    Authenticated,
    ALL_PERMISSIONS,
    Allow,
)
from sqlalchemy import or_

from .base import (
    FormView,
    GridView,
)
from ..models import (
    Employee,
    Address,
    Phone,
    User,
    Department,
    EmployeeGroup,
)
from ..schemas import (
    EmployeeSchema,
    AddressSchema,
    PhoneSchema,
    LoginSchema,
    DepartmentSchema,
)
from ..renderers import Form


def get_required_permission():
    return [None, 'ADMIN'][len(User.query().all()) > 0]


class Employees(GridView, FormView):
    # permissions for (/hris/employees)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, 'R:ADMINISTRATOR', ALL_PERMISSIONS),
    ]
    __model__ = Employee

    def index(self):
        return self.grid_index({
            'title': 'Employees',
            'description': 'register/update employee information',
        })

    def grid_data(self):
        query = Employee.query()
        query.page_index = int(self.request.params.get('page') or 1)

        search_params = self.request.POST
        status = search_params.get('status')
        kw = search_params.get('keyword')

        if status:
            query = query.filter(status=status)
        if kw:
            query = query.filter(or_(
                Employee.last_name.contains(kw),
                Employee.first_name.contains(kw)
            ))

        return self.shared_values({
            'current_page': query.order_by(
                Employee.last_name,
                Employee.first_name,
            )
        })

    def create(self):
        return self.form_index({
            'title': 'New Employee',
            'description': 'register new employee'
        })

    def update(self):
        return self.form_index({
            'title': 'Update Employee',
            'description': 'update employee registration',
        })

    def form_wrapper(self):
        employee = self.request.context
        if employee is None or not isinstance(employee, Employee):
            employee = Employee(status='Active')

        # remove employee Role from post if not admin
        if 'submit' in self.request.POST \
                and 'login.role' in self.request.POST \
                and not self.request.has_permission('ADMIN'):
            self.request.POST.pop('login.role')

        return Form(self.request, EmployeeSchema, employee)

    def form_renderer(self, form):
        return self.shared_values(super().form_renderer(form))

    def address_row(self):
        return self.sub_form(Address(type='Office'), AddressSchema)

    def phone_row(self):
        return self.sub_form(Phone(type='Office'), PhoneSchema)

    def login(self):
        return self.sub_form(User(), LoginSchema)

    def group(self):
        group_id = self.request.params.get('id')
        return {
            'row_id': self.request.params.get('row_id'),
            'group': EmployeeGroup(department_id=group_id)
        }

    def shared_values(self, values):
        has_permission = self.request.has_permission('EDIT')
        departments = Department.query().order_by(Department.name).all()
        department_list = [(d.name, d.id)for d in departments]
        values.update({
            'department_list': department_list,
            'has_permission': has_permission
        })
        return values

    @classmethod
    def add_views(cls, config):
        super().add_views(config)

        cls.register_view(config,
                          route_name='action',
                          attr='address_row',
                          renderer='address_row.pt')
        cls.register_view(config,
                          route_name='action',
                          attr='phone_row',
                          renderer='phone_row.pt')
        cls.register_view(config,
                          route_name='action',
                          attr='login',
                          renderer='login.pt')
        cls.register_view(config,
                          route_name='action',
                          attr='group',
                          renderer='group.pt')


class Departments(GridView, FormView):
    # permissions for (/crm/departments)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, 'D:ITD', 'EDIT'),
    ]

    use_global_form_template = False
    use_form_macros = False

    def index(self):
        return self.grid_index({
            'title': 'Departments',
            'description': 'create/update departments',
        })

    def grid_data(self):
        query = Department.query()
        query.page_index = int(self.request.params.get('page') or 1)

        search_params = self.request.POST
        kw = search_params.get('keyword')

        if kw:
            query = query.filter(Department.name.startswith(kw))

        return {
            'current_page': query.order_by(
                Department.id,
                Department.name
            )
        }

    def search_box(self, template_name='erp:templates/hris/departments/search_box.pt'):
        return super().search_box(template_name)

    def form_wrapper(self):
        department_id = self.request.matchdict.get('id') or \
                     self.request.POST.get('id')

        department = Department.find(id=department_id) or Department()

        return Form(self.request, DepartmentSchema, department)

    def delete(self):
        data = self.decode_request()
        ids = data.get('id')
        status = data.get('new-status')
        if ids and status:
            departments = Department.filter(Department.id.in_(ids))
            departments.delete(synchronize_session=False)

        return self.grid()

    @classmethod
    def add_views(cls, config):
        super().add_views(config)
        cls.register_view(config,
                          route_name='action',
                          attr='delete',
                          request_method='POST',
                          permission='EDIT')
