# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Sublcasses for read-only views of objects, supporting tooltips

from flask_table import Table, Col, LinkCol

class ViewCol(Col):
    def td_contents(self, i, attr_list):
        if 'tooltip' in i:
            self.td_html_attrs['data-placement'] = 'top'
            self.td_html_attrs['data-container'] = 'body'
            self.td_html_attrs['data-toggle'] = 'tooltip'
            self.td_html_attrs['title'] = i['tooltip']
        else:
            self.td_html_attrs['title'] = ''
        foo = self.td_format(self.from_attr_list(i, attr_list))
        return foo