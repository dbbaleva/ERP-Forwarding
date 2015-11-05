from reportlab.lib import colors
from reportlab.lib import units

from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table, TableStyle)

from reportlab.lib.styles import (
    ParagraphStyle,
)

from reportlab.lib.enums import (
    TA_LEFT,
    TA_CENTER
)

from .util import *


class InteractionsSummary(BaseDocTemplate):
    stylesheet = {
        'default': ParagraphStyle(
            name='default',
            fontName='Helvetica',
            fontSize=8,
            leading=9,
        )
    }

    stylesheet['header_title'] = ParagraphStyle(
        name='header_title',
        parent=stylesheet['default'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=13,
        alignment=TA_CENTER,
    )

    stylesheet['header_text'] = ParagraphStyle(
        name='header_title',
        parent=stylesheet['default'],
        alignment=TA_CENTER,
    )

    stylesheet['report_title'] = ParagraphStyle(
        name='report_title',
        parent=stylesheet['default'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=11,
        alignment=TA_CENTER,
    )

    stylesheet['table-title'] = TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 8, 9),
        ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 8, 9),
        ('FONT', (0, 1), (-1, 1), 'Helvetica-Bold', 8, 9),
        ('LINEABOVE', (0, 1), (-1, 1), 0.5, colors.black),
        ('LINEBELOW', (0, 1), (-1, 1), 0.5, colors.black),

    ])
    stylesheet['table-header'] = TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 8, 9),
    ])
    stylesheet['table-row'] = TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 8, 9),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    def __init__(self, data, **kwargs):
        super().__init__(generate_random_filename(), **kwargs)
        self.leftMargin = self.topMargin = self.bottomMargin = self.rightMargin = 0.5 * units.inch
        self._calc()
        self.data = data

    @property
    def header(self):
        return [
            Paragraph('FAMOUS PACIFIC FORWARDING PHILS., INC.', self.stylesheet['header_title']),
            Paragraph('26th Floor Trident Tower, 312 Sen. Gil Puyat Ave., Makati City', self.stylesheet['header_text']),
            Spacer(self.width, 14),
            Paragraph('INTERACTION SUMMARY', self.stylesheet['report_title']),
        ]

    def handle_pageBegin(self):
        '''override base method to add a change of page template after the firstpage.
        '''
        self._handle_pageBegin()
        self._handle_nextPageTemplate('later_pages')

    def wrap_y(self, flowables):
        height = 0
        for f in flowables:
            w, h = f.wrap(self.width, self.height)
            height = height + h
        return height

    def build_templates(self):
        header_height = self.wrap_y(self.header)
        self.pageTemplates = [
            PageTemplate(
                id='first_page',
                frames=[
                    Frame(self.leftMargin,
                          self.bottomMargin,
                          self.width,
                          self.height - (header_height + 5 * units.mm),
                          leftPadding=0,
                          bottomPadding=0,
                          topPadding=0,
                          rightPadding=0)
                ],
                onPage=self.draw_header
            ),
            PageTemplate(
                id='later_pages',
                frames=[
                    Frame(self.leftMargin,
                          self.bottomMargin,
                          self.width,
                          self.height,
                          showBoundary=1)
                ]
            )
        ]

    def draw_header(self, canv, doc):
        canv.saveState()
        header_height = self.wrap_y(self.header)
        top = self.pagesize[1] - self.topMargin

        frame = Frame(self.leftMargin,
                      top - header_height,
                      self.width,
                      header_height,
                      leftPadding=0,
                      bottomPadding=0,
                      topPadding=0,
                      rightPadding=0)
        frame.addFromList(self.header, canv)
        canv.restoreState()

    def build_stories(self):
        data = list(self.data.all())
        account_name = None
        entry_date = ''
        story = []
        for item in data:
            if account_name != item.account.name.upper():
                story.append(Table(
                    [
                        ['AE/STAFF', item.account.name.upper(), ''],
                        ['DATE', 'COMPANY', 'SUBJECT'],
                    ],
                    style=self.stylesheet['table-title'],
                    colWidths=[70, 215, 215]
                ))
                account_name = item.account.name.upper()

            if entry_date != item.entry_date.strftime('%m/%d/%Y'):
                entry_date = item.entry_date.strftime('%m/%d/%Y')
            else:
                entry_date = ''

            story.append(Table(
                [
                    [entry_date, item.company.name.upper(), item.subject.upper()],
                ],
                style=self.stylesheet['table-header'],
                colWidths=[70, 215, 215]
            ))
            details = item.details.strip('<br>')
            story.append(Table(
                [
                    ['', Paragraph(text=details, style=self.stylesheet['default'])],
                ],
                style=self.stylesheet['table-row'],
                colWidths=[70, 430]
            ))

        return story

    def build_pdf(self):
        story = self.build_stories()
        self.build_templates()
        self.build(story, canvasmaker=NumberedCanvas)

    def generate(self):
        self.build_pdf()
        with open(self.filename, mode='rb') as f:
            b = f.read()
        delete_files(self.filename)
        if b:
            return b.decode('latin1')
