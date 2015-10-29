from pyramid.security import (
    Authenticated,
    ALL_PERMISSIONS,
    Allow,
)
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
    UserDepartment,
)
from ..schemas import (
    EmployeeSchema,
    AddressSchema,
    PhoneSchema,
    LoginSchema,
    DepartmentSchema,
)
from ..renderers import Form
from sqlalchemy import or_


def get_required_permission():
    return [None, 'ADMIN'][len(User.query().all()) > 0]


class Employees(GridView, FormView):
    # permissions for (/hris/employees)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, Authenticated, 'EDIT'),
        (Allow, 'D:ITD', ALL_PERMISSIONS),
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
            query = query.filter(Employee.status == status)
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

        return Form(self.request, EmployeeSchema, employee)

    def form_renderer(self, form):
        return self.shared_values(super().form_renderer(form))

    def address_row(self):
        return self.sub_form(Address(type='Office'), AddressSchema)

    def phone_row(self):
        return self.sub_form(Phone(type='Office'), PhoneSchema)

    def login(self):
        return self.sub_form(User(), LoginSchema, {
            'department_list':
                Department.query().order_by(Department.name).all()
        })

    def role(self):
        role_id = self.request.params.get('id')
        return {
            'row_id': self.request.params.get('row_id'),
            'role': UserDepartment(department_id=role_id)
        }

    def shared_values(self, values):
        has_permission = 'D:ITD' in self.request.effective_principals or \
                len(User.query().all()) == 0
        values.update({
            'department_list': Department.query().order_by(Department.name).all(),
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
                          attr='role',
                          renderer='role.pt')


class Departments(GridView, FormView):
    # permissions for (/crm/departments)
    __permissions__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, 'D:ITD', ALL_PERMISSIONS),
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

