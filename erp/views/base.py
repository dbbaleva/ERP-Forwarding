from pyramid.renderers import (
    render,
    get_renderer,
)
from pyramid.response import Response
from pyramid.security import ALL_PERMISSIONS
from ..renderers import (
    Form,
    FormRenderer,
    decode_request_data
)


########################################################
# Helpers
########################################################
def _get_module(cls):
    if isinstance(cls, BaseView):
        return cls.__class__.__module__.split('.')[-1]


def _get_class_name(cls):
    if isinstance(cls, BaseView):
        return cls.__class__.__name__.lower()


def _test_renderer(renderer_name):
    from pyramid.path import AssetResolver
    resolver = AssetResolver()
    path = resolver.resolve(renderer_name).abspath()
    return path


def get_renderer_name(*args):
    args = ['erp:templates', ] + list(args)
    return '/'.join(args)


########################################################
# Base Classes
########################################################
class BaseView(object):
    # view model
    __model__ = None

    # model schema
    __schema__ = None

    def __init__(self, request):
        self.request = request

    @classmethod
    def register_view(cls, config, **kwargs):
        params = {
            'module': cls.__module__.split('.')[-1],
            'cls': cls.__name__.lower()
        }

        action = kwargs.pop('action', None)
        attr = kwargs.pop('attr', None)
        renderer = kwargs.pop('renderer', None)
        shared = kwargs.pop('shared', None)
        permission = kwargs.pop('permission', 'VIEW')

        if attr and attr != 'index' and not action:
            action = attr

        if action:
            params.update({'action': action})

        match_param = ['%s=%s' % (k, v) for k, v in params.items()]

        if renderer:
            if shared:
                renderer = get_renderer_name(renderer)
            else:
                renderer = get_renderer_name(params.get('module'),
                                             params.get('cls'),
                                             renderer)

        config.add_view(cls,
                        attr=attr,
                        match_param=match_param,
                        renderer=renderer,
                        permission=permission,
                        **kwargs)

    @classmethod
    def add_views(cls, config):
        pass


class GridView(BaseView):
    """
    Use the default global index.pt template
    """
    use_global_index_template = True

    def index(self):
        return self.grid_index()

    def search_box(self, template_name=None):
        """
        Returns the search_box template
        Usage:: index.pt : <div class="search_box" tal:content="structure search_box">
        """
        template_name = template_name or 'erp:templates/search_box.pt'
        return render(template_name, {
            'search_url': self.request.route_url(
                route_name='action',
                action='grid',
                module=_get_module(self),
                cls=_get_class_name(self)
            )
        }, self.request)

    def grid_index(self, values=None):
        _values = {
            'search_box': self.search_box(),
            'grid_view': self.grid_view(),
            'macros': self.grid_macros
        }

        if values:
            _values.update(values)

        return _values

    def grid(self):
        """
        Returns the grid view to response.
        Usage:: URL: /options/companies/grid
        """
        return Response(self.grid_view())

    def grid_view(self):
        """
        Returns the grid view template.
        Usage:: index.pt: <div class="grid content" tal:content="structure grid_view">
        """
        renderer_name = \
            get_renderer_name(_get_module(self),
                              _get_class_name(self),
                              'grid_view.pt')

        return render(renderer_name, self.grid_data(), self.request)

    @property
    def grid_macros(self):
        renderer_name = \
            get_renderer_name(_get_module(self),
                              _get_class_name(self),
                              'grid_macros.pt')

        return get_renderer(renderer_name).implementation()

    def query_model(self, **kwargs):
        if self.__model__ and hasattr(self.__model__, 'query'):

            with_permissions = kwargs.pop('with_permissions', True)
            all_dept_rows = kwargs.pop('all_dept_rows', False)
            has_all_permissions = self.request.has_permission(ALL_PERMISSIONS)

            if has_all_permissions or not with_permissions:
                query = self.__model__.query()
            else:
                user = self.request.authenticated_user
                query = self.__model__.query_with_permissions(user, all_dept_rows)

            query.page_index = int(self.request.params.get('page') or 1)

            return query

    def grid_data(self):
        return {}

    @classmethod
    def add_views(cls, config):
        super().add_views(config)
        cls.register_view(config,
                          shared=cls.use_global_index_template,
                          route_name='index',
                          attr='index',
                          renderer='index.pt')
        cls.register_view(config,
                          route_name='action',
                          attr='grid')


class FormView(BaseView):
    """
    Use the default global form.pt template
    """
    use_global_form_template = True
    use_form_macros = True

    def create(self):
        """
        Usage:: URL: /options/companies/create
        """
        return self.form_index({
            # values
        })

    def update(self):
        """
        Usage:: URL: /options/companies/update
        """
        return self.form_index({
            # values
        })

    def form_index(self, values=None):
        form = self.form_wrapper()
        form.update(values)
        return form

    def form_wrapper(self):
        """
        Handles form create/update methods
        """
        form = Form(self.request,
                    self.__schema__,
                    self.request.context)

        if self.request.method == 'GET':
            return {
                'form_view': self.form_view(form),
                'form_url': self.form_url,
                'macros': self.form_macros if self.use_form_macros else '',
            }
        elif 'submit' in self.request.POST and form.validate():
            self.before_save()
            form.save_data()

        return Response(self.form_view(form))

    def form_view(self, form):
        """
        Returns the actual form view
        """
        renderer_name = \
            get_renderer_name(_get_module(self),
                              _get_class_name(self),
                              'form_view.pt')

        values = self.form_values(form) or {}
        values.update({
            'form': FormRenderer(form)
        })

        return render(renderer_name, values, self.request)

    def form_values(self, form):
        """Shared form dictionary values"""
        pass

    def before_save(self):
        """Override this method to perform additional tasks before saving to the database"""
        pass

    @property
    def form_url(self):
        return self.request.route_url(
                    route_name='action',
                    action='update',
                    module=_get_module(self),
                    cls=_get_class_name(self))

    @property
    def form_macros(self):
        """
        Returns the form_macros.pt template.
        Sample form_macros.pt:
        <tal:block metal:define-macro="header">
            <link href="${request.static_url('erp:lib/bootstrap-datetimepicker.min.css')}" rel="stylesheet">
        </tal:block>

        <tal:block metal:define-macro="footer">
            <script src="${request.static_url('erp:lib/jquery.validate.min.js')}"></script>
            <script src="${request.static_url('erp:lib/moment.min.js')}"></script>
            <script src="${request.static_url('erp:lib/bootstrap-datetimepicker.min.js')}"></script>
            <script src="${request.static_url('erp:static/js/site.js')}"></script>
        </tal:block>
        """
        renderer_name = \
            get_renderer_name(_get_module(self),
                              _get_class_name(self),
                              'form_macros.pt')

        return get_renderer(renderer_name).implementation()

    def form_grid(self, schema, name=None):
        """
        Handles form and inline grid editing
        """
        row_id = self.request.params.get('row_id', self.request.POST.get('row_id'))
        form = Form(self.request, schema)
        action = self.request.matchdict.get('action')
        if 'row' in action and form.validate(auto_update=False):
            name = name or schema.model.__name__.lower()
            return {
                name: form.data,
                'row_id': row_id,
            }

        if 'edit' in action:
            return {
                'form': FormRenderer(form),
                'row_id': row_id,
            }

    def sub_form(self, model, schema, values=None):
        """
        Handles sub-form editing.
        Sample implementation address_row.pt
        """
        form = Form(self.request, schema, model)
        _values = {
            'form': FormRenderer(form),
            'row_id': self.request.params.get('row_id'),
        }
        if values:
            _values.update(values)

        return _values

    def decode_request(self):
        return decode_request_data(self.request)

    @classmethod
    def add_views(cls, config):
        super().add_views(config)
        cls.register_view(config,
                          shared=cls.use_global_form_template,
                          route_name='action',
                          attr='create',
                          renderer='form.pt',
                          request_method='GET',
                          permission='EDIT')
        cls.register_view(config,
                          shared=cls.use_global_form_template,
                          route_name='action',
                          attr='update',
                          request_method='GET',
                          permission='VIEW',
                          renderer='form.pt')
        cls.register_view(config,
                          shared=cls.use_global_form_template,
                          route_name='action',
                          action='update',
                          attr='form_wrapper',
                          request_method='POST',
                          permission='EDIT',
                          renderer='form.pt')
        cls.register_view(config,
                          shared=cls.use_global_form_template,
                          route_name='action',
                          action='form',
                          attr='form_wrapper',
                          renderer='form.pt')
        cls.register_view(config,
                          shared=cls.use_global_form_template,
                          route_name='action_id',
                          attr='update',
                          renderer='form.pt')
