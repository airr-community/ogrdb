# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# subclasses for flask_table that impose styles we want and allow columnm header text to be rotated and to have tooltips
from markupsafe import Markup
from flask_table import Table, Col, LinkCol, DateCol
from flask_table.html import element
from sequence_format import *


class StyledTable(Table):
    def __init__(self, *args, **kwargs):
        self.rotate_header = False

        if 'classes' not in kwargs:
            kwargs['classes'] = []

        self.empty_message = kwargs.get('empty_message', 'No Items')
        if 'empty_message' in kwargs:
            del(kwargs['empty_message'])

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

    def __html__(self):
        ret =  super(StyledTable, self).__html__()
        if 'No Items' in ret:
            ret = '<div class="%s">'% ' '.join(self.classes) + self.empty_message + '</div>'
        return ret

class StyledCol(Col):
    def __init__(self, *args, **kwargs):
        if 'tooltip' in kwargs:
            kwargs['th_html_attrs'] = {'class': 'th_back', 'data-toggle':"tooltip", 'data-placement': 'top', 'data-container': 'body', 'title': kwargs['tooltip']}
            del(kwargs['tooltip'])
        else:
            kwargs['th_html_attrs'] = {'class': 'th_back'}

        super(StyledCol, self).__init__(*args, **kwargs)


class StyledDateCol(DateCol):
    def __init__(self, *args, **kwargs):
        if 'tooltip' in kwargs:
            kwargs['th_html_attrs'] = {'class': 'th_back', 'data-toggle':"tooltip", 'data-placement': 'top', 'data-container': 'body', 'title': kwargs['tooltip']}
            del(kwargs['tooltip'])
        else:
            kwargs['th_html_attrs'] = {'class': 'th_back'}

        if 'date_format' not in kwargs:
            kwargs['date_format'] = 'y-MM-dd'

        super(StyledDateCol, self).__init__(*args, **kwargs)


class StyledLinkCol(LinkCol):
    def __init__(self, *args, **kwargs):
        kwargs['th_html_attrs'] = {'class': 'th_back'}
        super(StyledLinkCol, self).__init__(*args, **kwargs)


class HiddenCol(Col):
    def __init__(self, *args, **kwargs):
        #kwargs['th_html_attrs'] = {'class': 'collapsed, row-0'}
        #kwargs['td_html_attrs'] = {'class': 'collapsed, row-0'}

        super(HiddenCol, self).__init__(*args, **kwargs)



