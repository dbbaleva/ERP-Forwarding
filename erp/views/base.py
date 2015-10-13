from pyramid.renderers import (
    render,
    get_renderer,
)
from ..renderers import (
    Form,
    FormRenderer,
)
from pyramid.response import Response


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


def _try_pop(obj, key, value_if_none=None):
    if key in obj:
        return obj.pop(key)
    return value_if_none


def get_renderer_name(*args):
    args = ['erp:templates', ] + list(args)
    return '/'.join(args)


########################################################
# Base Classes
########################################################
class BaseView(object):
    def __init__(self, request):
        self.request = request

    @classmethod
    def register_view(cls, config, **kwargs):
        params = {
            'module': cls.__module__.split('.')[-1],
            'cls': cls.__name__.lower()
        }

        action = _try_pop(kwargs, 'action')
        permission = _try_pop(kwargs, 'permission')
        attr = _try_pop(kwargs, 'attr')
        renderer = _try_pop(kwargs, 'renderer')
        shared = _try_pop(kwargs, 'shared')

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
                        permission=permission,
                        attr=attr,
                        match_param=match_param,
                        renderer=renderer,
                        **kwargs)

    @classmethod
    def views(cls, config):
        pass


class GridView(BaseView):
    """
    Use the default global index.pt template
    """
    use_global_index_template = True

    def index(self):
        return self.index_view()

    def index_view(self, values=None):
        _values = {
            'search_box': self.search_box(),
            'grid_view': self.grid_view(),
            'macros': self.grid_macros()
        }

        if values:
            _values.update(values)
        return _values

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

    def grid_macros(self):
        renderer_name = \
            get_renderer_name(_get_module(self),
                              _get_class_name(self),
                              'grid_macros.pt')

        return get_renderer(renderer_name).implementation()

    def grid_data(self):
        return {}

    @classmethod
    def views(cls, config):
        super().views(config)
        cls.register_view(config, shared=cls.use_global_index_template,
                          route_name='index', attr='index', renderer='index.pt')
        cls.register_view(config, route_name='action', attr='grid', renderer='grid.pt')


class FormView(BaseView):
    """
    Use the default global form.pt template
    """
    use_global_form_template = True

    def create(self):
        """
        Usage:: URL: /options/companies/create
        """
        return self.form()

    def update(self):
        """
        Usage:: URL: /options/companies/update
        """
        return self.form()

    def form(self, values=None):
        """
        Handles form create/update methods
        """
        form = self.form_wrapper()

        if self.request.method == 'GET':
            _values = {
                'form_view': self.form_view(form),
                'form_url': self.request.route_url(
                    route_name='action',
                    action='update',
                    module=_get_module(self),
                    cls=_get_class_name(self))
            }

            macros = self.form_macros()
            if macros:
                _values.update({'macros': macros})

            if values:
                _values.update(values)

            return _values

        elif 'submit' in self.request.POST and form.validate():
            form.save_data()

        return Response(self.form_view(form))

    def form_view(self, form, values=None):
        """
        Returns the actual form view
        """
        renderer_name = \
            get_renderer_name(_get_module(self),
                              _get_class_name(self),
                              'form_view.pt')
        _values = {
            'form': FormRenderer(form)
        }
        if values:
            _values.update(values)

        return render(renderer_name, _values, self.request)

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

    def form_wrapper(self):
        """
        Override this method and should return a Form object.

        Sample implementation:
        company_id = self.request.matchdict.get('id') or \
                     self.request.POST.get('id')

        if company_id:
            company = Company.find(id=company_id)
        else:
            company = Company(status='Active')

        return Form(self.request, CompanySchema, company)
        """
        pass

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

    @classmethod
    def views(cls, config):
        super().views(config)
        cls.register_view(config, shared=cls.use_global_form_template,
                          route_name='action', attr='create', renderer='form.pt')
        cls.register_view(config, shared=cls.use_global_form_template,
                          route_name='action', attr='update', renderer='form.pt')
        cls.register_view(config, shared=cls.use_global_form_template,
                          route_name='action', attr='form', renderer='form.pt')
        cls.register_view(config, shared=cls.use_global_form_template,
                          route_name='action_id', attr='update', renderer='form.pt')