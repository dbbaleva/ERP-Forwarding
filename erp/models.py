import os
from binascii import hexlify
from datetime import datetime
from passlib.hash import sha256_crypt as password_hash
from pyramid.request import Request
from pyramid.security import (
    Allow,
    Deny,
    Authenticated,
    Everyone,
    ALL_PERMISSIONS
)
from sqlalchemy.orm import (
    backref,
    relationship,
    scoped_session,
    sessionmaker,
)
from sqlalchemy import (
    func,
    Column,
    Date,
    DateTime,
    Integer,
    SmallInteger,
    Numeric,
    String,
    Unicode,
)
from sqlalchemy.orm.query import Query
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import (
    as_declarative,
    declared_attr
)
from sqlalchemy.schema import ForeignKey
from zope.sqlalchemy import ZopeTransactionExtension


####################################################################################
# Utility methods
####################################################################################

def create_association(cls, assoc_table, relationship_name):
    """
    Creates a relationship as relationship_name to the assoc_table for each parent
    """
    name = cls.__name__
    discriminator = name.lower()
    association_name = assoc_table.__tablename__

    assoc_cls = type(  # creates dynamic class
        '{cls_name}{assoc_name}'.format(
            cls_name=name,
            assoc_name=assoc_table.__name__
        ),  # name, i.e. EmployeeAddressMap
        (assoc_table,),  # base
        dict(  # attributes
               __tablename__=None,
               __mapper_args__={
                   'polymorphic_identity': discriminator
               }
               )
    )

    setattr(cls, relationship_name, association_proxy(
        association_name,
        relationship_name,
        creator=lambda obj: assoc_cls(**{relationship_name: obj})
    ))

    return relationship(assoc_cls,
                        backref=backref('parent', uselist=False))


def generate_random_digest(num_bytes=28):
    """Generates random hash and returns the digest as string."""
    r = os.urandom(num_bytes)
    return hexlify(r).decode('utf-8')


def generate_uid(context=None):
    uid = None

    if context:
        uid = context.current_parameters['id']

    if uid is None:
        return generate_random_digest(num_bytes=64)


def generate_confirmation_hash():
    return generate_random_digest(num_bytes=14)


####################################################################################
# Super base classes
####################################################################################
class GridQuery(Query):
    page_index = 1
    page_size = 25

    def __init__(self, entities, session=None):
        super().__init__(entities, session)

    def rows(self, offset=1, size=25):
        """
        Returns the current page rows
        """
        self.page_index = self.page_index or offset
        self.page_size = self.page_size or size
        return self.offset(self.page_index - 1).limit(self.page_size).all()

    def to_json(self, columns=None):
        data_list = [
            item.__json__(columns) for item in self.rows() if hasattr(item, '__json__')
        ]
        return data_list

    @property
    def total_row_count(self):
        return self.count()

    @property
    def page_count(self):
        """ Returns the number of pages according to page size
        """
        count = self.count()
        size = self.page_size
        offset = 1 if (count % size) > 0 else 0
        return int(count / size) + offset

    @property
    def first_row(self):
        """ Returns the first row of the current page
        """
        return 1 + (self.page_index - 1) * self.page_size

    @property
    def last_row(self):
        """ Returns the last row of the current page
        """
        last_page = self.page_index * self.page_size
        return last_page if last_page < self.total_row_count else self.total_row_count


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension(), query_cls=GridQuery))


@as_declarative()
class Base(object):
    def __init__(self, **kwargs):
        for k in kwargs:
            if not hasattr(self, k):
                raise TypeError(
                    '%r is an invalid keyword argument for %s' %
                    (k, self.__name__))
            setattr(self, k, kwargs[k])

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def save(self, request):
        session = DBSession()
        session.add(self)

        for obj in list(session.new) + list(session.dirty):
            if isinstance(obj, Audited):
                obj.audit(request)

        session.flush()

    def __json__(self, columns=None):
        if columns and isinstance(columns, dict):
            data = dict([(k, self._to_json(v)) for k, v in columns.items()])
            return data

        columns = [c.key for c in self.__table__.columns]
        data = dict((c, self._to_json(c)) for c in columns)
        return data

    def _to_json(self, key):
        value = getattr(self, key)
        if isinstance(value, datetime):
            value = value.isoformat()
        return value

    @classmethod
    def query(cls):
        return DBSession.query(cls)

    @classmethod
    def query_with_permissions(cls, user, all_dept_rows=False):
        query = cls.query()
        if hasattr(cls, 'created_by'):
            employee = user.profile
            departments = list(employee.departments)
            # query rows based on user's role
            if user.role == 'Supervisor':
                # staff, supervisor rows
                user_ee_dept = User.query()\
                    .join(Employee, User.id == Employee.user_id)\
                    .join(EmployeeGroup, Employee.id == EmployeeGroup.employee_id)\
                    .filter(
                        User.role.in_([None, 'Staff', 'Supervisor']),
                        EmployeeGroup.department_id.in_(['MKG'])
                ).subquery()
                query = query.join(user_ee_dept, cls.created_by == user_ee_dept.c.id)

            elif user.role == 'Manager' or \
                    all_dept_rows:
                # all rows
                user_ee_dept = User.query()\
                    .join(Employee, User.id == Employee.user_id)\
                    .join(EmployeeGroup, Employee.id == EmployeeGroup.employee_id)\
                    .filter(
                        EmployeeGroup.department_id.in_(departments)
                ).subquery()
                query = query.join(user_ee_dept, cls.created_by == user_ee_dept.c.id)

            else:
                # current user rows only
                query = query.filter(cls.created_by == user.id)

        return query

    @classmethod
    def filter(cls, *criterion):
        return cls.query().filter(*criterion)

    @classmethod
    def filter_by(cls, **criterion):
        return cls.query().filter_by(**criterion)

    @classmethod
    def find(cls, **criterion):
        return cls.query().filter_by(**criterion).first()


class Audited(object):
    _request = None

    def __init__(self):
        self.created_at = None
        self.created_by = None
        self.updated_by = None
        self.updated_at = None

    @property
    def __acl__(self):
        owner = self.owner
        employee = owner.profile

        access_list = [
            (Allow, owner.username, 'VIEW'),
            (Allow, owner.username, 'EDIT'),
            (Allow, 'R:DIRECTOR', 'EDIT'),
            (Allow, 'R:DIRECTOR', 'VIEW'),
            (Allow, 'R:ADMINISTRATOR', ALL_PERMISSIONS),
        ]

        for d in employee.departments:
            access_list.append((Allow, 'D:%s' % d.upper(), 'VIEW'))

        access_list.append((Deny, Everyone, ALL_PERMISSIONS))

        return access_list

    @declared_attr
    def created_by(cls):
        return Column('created_by', Unicode(128), ForeignKey('user.id'), nullable=False)

    @declared_attr
    def created_at(cls):
        return Column('created_at', DateTime, nullable=False)

    @declared_attr
    def updated_by(cls):
        return Column('updated_by', Unicode(128), ForeignKey('user.id'), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column('updated_at', DateTime, nullable=False)

    @declared_attr
    def owner(cls):
        name = cls.__name__
        return relationship('User', foreign_keys='{cls}.created_by'.format(cls=name))

    def audit(self, request=None, user=None):
        if request and isinstance(request, Request) and not user:
            user = request.authenticated_user

        if not self.created_by:
            self.created_by = user.id
        if not self.created_at:
            self.created_at = datetime.now()

        self.updated_by = user.id
        self.updated_at = datetime.now()


class AssociationMap(object):
    """Associates a collection of objects with a particular parent.
    """

    discriminator = Column(String)
    """Refers to the type of parent."""

    __mapper_args__ = {'polymorphic_on': discriminator}


####################################################################################
# Table bases
####################################################################################
class AddressMap(AssociationMap, Base):
    __tablename__ = 'address_map'
    id = Column(Integer, primary_key=True)


class HasAddresses(object):
    @declared_attr
    def address_map_id(cls):
        return Column(Integer, ForeignKey('address_map.id'))

    @declared_attr
    def address_map(cls):
        return create_association(cls, AddressMap, 'addresses')

    @property
    def default_address(self):
        if self.addresses:
            return self.addresses[0].description
        else:
            return 'No address, please input at least one'


class PhoneMap(AssociationMap, Base):
    __tablename__ = 'phone_map'
    id = Column(Integer, primary_key=True)


class HasPhoneNumbers(object):
    @declared_attr
    def phone_map_id(cls):
        return Column(Integer, ForeignKey('phone_map.id'))

    @declared_attr
    def phone_map(cls):
        return create_association(cls, PhoneMap, 'phone_numbers')

    @property
    def default_phone(self):
        if hasattr(self, 'phone_numbers') and self.phone_numbers:
            return self.phone_numbers[0].number
        else:
            return 'No phone, please input at least one'


####################################################################################
# Actual table definitions
####################################################################################
class Address(Base):
    id = Column(Integer, primary_key=True)
    description = Column(Unicode)
    type = Column(String(15))

    map_id = Column(Integer, ForeignKey('address_map.id'))
    association = relationship('AddressMap', backref='addresses')
    parent = association_proxy('association', 'parent')

    def __repr__(self):
        return '%s(description=%r, type=%r)' % \
               (self.__class__.__name__,
                self.description,
                self.type)


class Phone(Base):
    id = Column(Integer, primary_key=True)
    number = Column(String(150))
    type = Column(String(15))

    map_id = Column(Integer, ForeignKey('phone_map.id'))
    association = relationship('PhoneMap', backref='phone_numbers')
    parent = association_proxy('association', 'parent')

    def __repr__(self):
        return '%s(number=%r, type=%r)' % \
               (self.__class__.__name__,
                self.number,
                self.type)


class Company(Base, Audited, HasAddresses, HasPhoneNumbers):
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(150), nullable=False)
    tin = Column(String(50))
    website = Column(String(50))
    account_id = Column(String(3), ForeignKey('account.id'))
    status = Column(String(15), nullable=False)
    contact_persons = relationship('ContactPerson', backref='company')
    company_miscs = relationship('CompanyMisc', backref='company')
    company_types = relationship('CompanyType', backref='company',
                                 cascade='save-update, merge, delete, delete-orphan')

    account = relationship('Account')

    def __repr__(self):
        return '%s(name=%r, status=%r)' % \
               (self.__class__.__name__,
                self.name,
                self.status)

    @property
    def __acl__(self):
        return [
            (Allow, Authenticated, 'VIEW'),
            (Allow, 'R:ADMINISTRATOR', ALL_PERMISSIONS),
            (Deny, Everyone, ALL_PERMISSIONS),
        ]

    def has_type(self, type_id):
        for t in self.company_types:
            if t.type_id == type_id:
                return True
        return False


class ContactPerson(Base):
    __tablename__ = 'contact_person'

    id = Column(Integer, primary_key=True)
    title = Column(String(10))
    name = Column(String(150), nullable=False)
    birth_date = Column(Date)
    position = Column(String(50))
    department = Column(String(50))
    phone = Column(String(50))
    email = Column(String(50))
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)

    def __repr__(self):
        return '%s(name=%r)' % \
               (self.__class__.__name__, self.name)


class CompanyType(Base):
    __tablename__ = 'company_type'

    type_id = Column(String(50), primary_key=True)
    company_id = Column(Integer, ForeignKey('company.id'), primary_key=True)

    def __repr__(self):
        return '%s(type=%r)' % \
               (self.__class__.__name__, self.type_id)


class CompanyMisc(Base):
    __tablename__ = 'company_misc'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(String(50), nullable=False)
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)

    def __repr__(self):
        return '%s(name=%r, description=%r)' % \
               (self.__class__.__name__,
                self.name, self.description)


class Employee(Base, Audited, HasAddresses, HasPhoneNumbers):
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    suffix = Column(String(10))
    gender = Column(String(10))
    birth_date = Column(Date)
    civil_status = Column(String(10))
    position = Column(String(30))
    user_id = Column(Unicode(128), ForeignKey('user.id'))
    status = Column(String(15), nullable=False)

    groups = relationship('EmployeeGroup', backref='employee',
                                 cascade='save-update, merge, delete, delete-orphan')

    departments = association_proxy('groups', 'department_id', creator=lambda d: EmployeeGroup(department_id=d))

    def __repr__(self):
        return '%s(name=%r, status=%r)' % \
               (self.__class__.__name__,
                self.fullname,
                self.status)

    @property
    def __acl__(self):
        return [
            (Allow, self.login.username, 'VIEW'),
            (Allow, self.login.username, 'EDIT'),
            (Allow, Authenticated, 'VIEW'),
            (Allow, 'R:ADMINISTRATOR', 'ADMIN'),
            (Allow, 'R:ADMINISTRATOR', ALL_PERMISSIONS),
            (Deny, Everyone, ALL_PERMISSIONS),
        ]

    @property
    def fullname(self):
        return ('{0} {1}'.format(self.first_name, self.last_name)).strip()


class Department(Base):
    id = Column(String(3), primary_key=True)
    name = Column(String(50), nullable=False)

    def __repr__(self):
        return '%s(name=%r)' % \
               (self.__class__.__name__,
                self.name)


class EmployeeGroup(Base):
    __tablename__ = 'employee_department'

    employee_id = Column(Integer, ForeignKey('employee.id'), primary_key=True)
    department_id = Column(String(3), ForeignKey('department.id'), primary_key=True)


class User(Base):
    id = Column(Unicode(128), default=generate_uid, primary_key=True)
    username = Column(Unicode(32), unique=True)
    password = Column(Unicode(128), nullable=False)
    # Staff, Supervisor, Manager, Director, Administrator
    role = Column(String(30), nullable=False)

    profile = relationship('Employee', uselist=False, backref='login', foreign_keys='Employee.user_id')

    def __init__(self, username=None, password=None, **kwargs):
        super().__init__(**kwargs)

        self.username = username
        self.password = User.hash_password(password)

    def __repr__(self):
        return '%s(username=%r)' % \
               (self.__class__.__name__,
                self.username)

    @property
    def fullname(self):
        return self.profile.fullname

    @classmethod
    def hash_password(cls, plain_text_password):
        if not plain_text_password:
            return None

        if isinstance(plain_text_password, str):
            plain_text_password = plain_text_password.encode('utf-8')

        return password_hash.encrypt(plain_text_password)

    @classmethod
    def validate_password(cls, plain_text_password, hashed_password):
        return password_hash.verify(plain_text_password, hashed_password)

    @classmethod
    def find(cls, username, id=None):
        criterion = [func.lower(User.username) == func.lower(username)]
        if id:
            criterion.append(User.id == id)

        return cls.filter(*criterion).first()

    @classmethod
    def validate(cls, username, password):
        user = cls.find(username)
        if user:
            return User.validate_password(password, user.password)


class Account(Base):
    id = Column(String(3), primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(50))

    def __repr__(self):
        return '%s(id=%r, name=%r)' % \
               (self.__class__.__name__,
                self.id, self.name)


class Interaction(Base, Audited):
    id = Column(Integer, primary_key=True)
    entry_date = Column(Date, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    followup_date = Column(DateTime)
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    contact_id = Column(Integer, ForeignKey('contact_person.id'), nullable=False)
    account_id = Column(String(3), ForeignKey('account.id'), nullable=False)
    subject = Column(Unicode(255), nullable=False)
    details = Column(Unicode, nullable=False)
    category = Column(String(15), nullable=False)
    status = Column(String(15), nullable=False)

    company = relationship('Company')
    contact = relationship('ContactPerson')
    account = relationship('Account')

    def __repr__(self):
        return '%s(subject=%r, account=%r, owner=%r)' % \
               (self.__class__.__name__,
                self.subject,
                self.account_id,
                self.owner.username)


class Quotation(Base, Audited):
    id = Column(Integer, primary_key=True)
    number = Column(String(20), nullable=False, unique=True)
    date = Column(Date, nullable=False)
    revision = Column(SmallInteger, nullable=False)
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    contact_id = Column(Integer, ForeignKey('contact_person.id'), nullable=False)
    account_id = Column(String(3), ForeignKey('account.id'), nullable=False)
    noted_by = Column(Integer, ForeignKey('employee.id'))
    classification = Column(String(3), nullable=False)
    credit_terms = Column(SmallInteger)
    effectivity = Column(Date, nullable=False)
    validity = Column(Date, nullable=False)
    remarks = Column(Unicode)
    status = Column(String(15), nullable=False)

    company = relationship('Company')
    contact = relationship('ContactPerson')
    account = relationship('Account')

    costings = relationship('QuotationCosting', backref='quotation')
    requirements = relationship('QuotationRequirement', backref='quotation')

    def __repr__(self):
        return '%s(company=%r, account=%r)' % (
            self.__class__.__name__,
            self.company.name,
            self.account_id
        )

    @property
    def default_requirement(self):
        if self.requirements:
            return self.requirements[0]
        return None

    @classmethod
    def generate_refno(cls, account_id):
        prefix = '{account}{date}'.format(
            account=account_id,
            date=datetime.today().strftime('%y%m')
        )

        query = cls.query().filter(
            cls.account_id == account_id,
            cls.number.startswith(prefix)
        )
        seed = query.count()

        return '{prefix}-{seed:03d}'.format(
            prefix=prefix,
            seed=seed+1
        )


class QuotationCosting(Base):
    __tablename__ = 'quotation_costing'

    id = Column(Integer, primary_key=True)
    group = Column(String(150), nullable=False)
    description = Column(String(150), nullable=False)
    currency = Column(String(3))
    rate = Column(Numeric)
    unit = Column(String(50))

    quotation_id = Column(Integer, ForeignKey('quotation.id'), nullable=False)


class QuotationRequirement(Base):
    __tablename__ = 'quotation_requirement'

    id = Column(Integer, primary_key=True)
    service_desc = Column(String(150), nullable=False)      # Commodity/Work Scope
    service_mode = Column(String(3), nullable=False)        # Import/Export/Domestic (IMP,EXP,DOM)
    service_type = Column(String(3), nullable=False)        # Seafreight/Airfreight (SFT,AFT)
    other_services = Column(String(12))                     # Brokerage, Moving, Trucking (BRK,MOV,TRK)
    origin = Column(String(150))
    destination = Column(String(150))

    quotation_id = Column(Integer, ForeignKey('quotation.id'), nullable=False)


####################################################################################
# Factories
####################################################################################
class RootFactory(object):
    __name__ = ''
    __parent__ = None
    __acl__ = [
        (Allow, Authenticated, 'VIEW'),
        (Allow, 'R:ADMINISTRATOR', 'ADMIN'),
        (Deny, Everyone, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class ViewFactory(object):
    @property
    def __acl__(self):
        if self.__view__ and hasattr(self.__view__, '__permissions__'):
            return self.__view__.__permissions__
        else:
            return [
                (Allow, Authenticated, 'VIEW'),
                (Allow, Authenticated, 'EDIT'),
                (Allow, 'D:ITD', 'EDIT'),
                (Deny, Everyone, ALL_PERMISSIONS),
            ]

    def __init__(self, request):
        module = request.matchdict.get('module')
        cls = request.matchdict.get('cls')

        if module and cls:
            name = 'erp.views.{module}.{cls}'.format(
                module=module,
                cls=cls.title()
            )
            self.__view__ = resolve(name)

        self.request = request

    def __getitem__(self, key):
        context = None

        if self.__view__ and hasattr(self.__view__, '__model__'):
            model = self.__view__.__model__
            model_id = self.request.matchdict.get('id') or self.request.POST.get('id')
            if model and model_id:
                context = model.find(id=model_id)

        if context:
            context.__parent__ = self
            context.__name__ = key
            return context

        self.__parent__ = None
        self.__name__ = key

        return self


def resolve(dotted):
    from pyramid.path import DottedNameResolver
    r = DottedNameResolver()
    return r.resolve(dotted)
