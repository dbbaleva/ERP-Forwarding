import re
import os
import xml.etree.ElementTree as ET
from pyramid.renderers import render

__APPS__ = {
    'ais': 'AIS',
    'crm': 'CRM',
    'hris': 'HRIS',
    'options': 'Options'
}


def parse_xml(file, xpath=None):
    here = os.path.dirname(__file__)
    source = os.path.join(here, 'static', 'xml', file)
    root = ET.parse(source).getroot()
    return root.findall(xpath) if xpath else root


class LefNav(object):
    current_path = ""

    def __init__(self, url):
        self.current_path = url

    def parse(self, file):
        root = parse_xml(file)
        return self.create_ul(root, 'main-menu')

    def create_ul(self, element, css):
        if len(element) == 0:
            return ''
        items = self.create_li(element)
        state = ' open' if 'active' in items else ''
        return '<ul class="{0}{2}">{1}</ul>'.format(css, items, state)

    def create_li(self, element):
        tag = ''
        for item in element:
            subitems = self.create_ul(item, 'sub-menu {0}'.format(item.get('state') or ''))
            url = item.get('url') or '#'
            state = 'active' if (url in self.current_path or 'active' in subitems) else ''
            css = 'class="{0}"'.format(state) if state == 'active' else ''
            anchor = self.create_anchor(item, state)
            tag += '<li {0}>{1}{2}</li>'.format(css, anchor, subitems)

        return tag

    def create_anchor(self, element, state):
        return '<a class="{0}" href="{1}">{3}<span class="text">{2}</span>{4}</a>'.format(
            'js-sub-menu-toggle' if len(element) > 0 else '',
            element.get('url') or '#',
            element.get('text'),
            self.create_icon(element),
            self.create_toggle(element, state),
        )

    @staticmethod
    def create_icon(element):
        icon = element.get('icon')
        return '<i class="fa {0} fa-fw"></i>'.format(icon) if icon else ''

    @staticmethod
    def create_toggle(element, state):
        css = 'down' if state == 'active' else 'left'
        return '<i class="toggle-icon fa fa-angle-{0}"></i>'.format(css) if len(element) > 0 else ''


def left_nav(file, url):
    return LefNav(url).parse(file)


class BreadCrumb(object):
    def __init__(self, request, title):
        self.current_path = request.path
        self.title = title

    def render(self):
        regex = re.compile(r'\d+')
        sections = [s for s in self.current_path.split('/') if len(s) > 0 and not regex.match(s)]
        return '<ul class="breadcrumb">{0}</ul>'.format(''.join(self.create_list(sections)))

    def create_list(self, sections):
        sections = sections[:-1] + [self.title.lower()]
        sections = self.remove_duplicates(sections)
        for i, s in enumerate(sections):
            if i == 0:  # first item
                yield '<li><i class="fa fa-home"></i><a href="#">{0}</a>&nbsp;</li>' \
                    .format(__APPS__.get(s.lower()))
            elif i == (len(sections) - 1):  # last item
                yield '<li class="active">{0}</li>'.format(s.title())
            else:  # next item
                yield '<li><a href="/{1}">{0}</a>&nbsp;</li>'.format(s.title(), '/'.join(sections[:i + 1]))

    def remove_duplicates(self, sequence):
        seen = set()
        seen_add = seen.add
        return [x for x in sequence if not (x in seen or seen_add(x))]


def breadcrumb(request, title):
    return BreadCrumb(request, title).render()


####################################################################################
# Request Helpers
####################################################################################
def quick_access(request):
    return render('erp:templates/quick_access.pt', {}, request)
