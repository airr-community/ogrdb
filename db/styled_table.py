# subclasses for flask_table that impose styles we want and allow columnm header text to be rotated and to have tooltips

from flask_table import Table, Col, LinkCol
from flask_table.html import element
from flask import Markup
from sequence_format import *


class StyledTable(Table):
    def __init__(self, *args, **kwargs):
        self.rotate_header = False

        if 'classes' not in kwargs:
            kwargs['classes'] = []

        kwargs['classes'] = list(kwargs['classes'])
        kwargs['classes'].append('table')
        kwargs['classes'].append('table_back')

        if 'rotate' in kwargs:
            self.rotate_header = kwargs['rotate']

        super(StyledTable, self).__init__(*args, **kwargs)

    def th(self, col_key, col):
        content = self.th_contents(col_key, col)
        attrs = col.th_html_attrs

        if self.rotate_header:
            content = Markup('<div><span>') + content + Markup('</span></div>')
            if 'class' in attrs:
                attrs['class'] += ' rotate'
            else:
                attrs['class'] = 'rotate'

        return element(
            'th',
            content = content,
            escape_content = False,
            attrs = attrs,
        )

class StyledCol(Col):
    def __init__(self, *args, **kwargs):
        if 'tooltip' in kwargs:
            kwargs['th_html_attrs'] = {'class':'th_back', 'data-toggle':"tooltip", 'data-placement':"top", 'data-container':"body", 'title':kwargs['tooltip']}
            del(kwargs['tooltip'])
        else:
            kwargs['th_html_attrs'] = {'class':'th_back'}

        super(StyledCol, self).__init__(*args, **kwargs)


class StyledLinkCol(LinkCol):
    def __init__(self, *args, **kwargs):
        kwargs['th_html_attrs'] = {'class':'th_back'}
        super(StyledLinkCol, self).__init__(*args, **kwargs)



