# Styled subclasses for flask_table

from flask_table import Table, Col, LinkCol

class StyledTable(Table):
    def __init__(self, *args, **kwargs):

        if 'classes' not in kwargs:
            kwargs['classes'] = []

        kwargs['classes'] = list(kwargs['classes'])
        kwargs['classes'].append('table')
        kwargs['classes'].append('table_back')

        super(StyledTable, self).__init__(*args, **kwargs)

    def rotate_header(self):
        # cheap hack. Assumes all th have the same class decorations
        # which they do, the way flask_table is written. But this really ought to be improved.
        tabletext = self.__html__()
        p = tabletext.find('<thead')
        p = tabletext.find('<th', p+1)
        q = tabletext.find('>', p)
        th = tabletext[p:q+1]
        thx = th[:-2] + ' rotate"><div><span>'
        tabletext = tabletext.replace(th, thx).replace('</th>', '</span></div></th>')
        return tabletext

class StyledCol(Col):
    def __init__(self, *args, **kwargs):
        kwargs['th_html_attrs'] = {'class':'th_back'}
        super(StyledCol, self).__init__(*args, **kwargs)

class StyledLinkCol(LinkCol):
    def __init__(self, *args, **kwargs):
        kwargs['th_html_attrs'] = {'class':'th_back'}
        super(StyledLinkCol, self).__init__(*args, **kwargs)



