# Styled subclasses for flask_table

from flask_table import Table, Col, LinkCol

class StyledTable(Table):
    def __init__(self, *args, **kwargs):
        kwargs['classes'] = ['table', 'table_back']
        super(StyledTable, self).__init__(*args, **kwargs)

class StyledCol(Col):
    def __init__(self, *args, **kwargs):
        kwargs['th_html_attrs'] = {'class':'th_back'}
        super(StyledCol, self).__init__(*args, **kwargs)

class StyledLinkCol(LinkCol):
    def __init__(self, *args, **kwargs):
        kwargs['th_html_attrs'] = {'class':'th_back'}
        super(StyledLinkCol, self).__init__(*args, **kwargs)

