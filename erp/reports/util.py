import os
from glob import glob
from pyramid.path import AssetResolver
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from ..models import generate_random_digest

__all__ = [
    'generate_random_filename',
    'delete_files',
    'NumberedCanvas'
]


def generate_random_filename(path=None, extension='pdf'):
    r = AssetResolver('erp')
    path = path or r.resolve('static/temp').abspath()
    if not os.path.exists(path):
        os.mkdir(path)
    filename = generate_random_digest()
    return '/'.join([path, '{filename}.{extension}'.format(filename=filename, extension=extension)])


def delete_files(expression):
    files = glob(expression)
    if files:
        os.remove(*files)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 7)
        self.drawRightString(200*mm, 10*mm,
            "Page %d of %d" % (self._pageNumber, page_count))
