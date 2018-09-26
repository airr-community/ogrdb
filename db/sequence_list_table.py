from flask import url_for
from copy import deepcopy

from db.styled_table import *
from db.gene_description_db import *

class SequenceListActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        fmt_string = []

        if item.viewable:
            fmt_string.append('<a href="%s">%s</a>'  % (url_for('sequence', id=item.id), item.sequence_name))
        else:
            fmt_string.append(item.submission_id)

        if item.editable:
            fmt_string.append('<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-pencil"></span>&nbsp;</a>'  % (url_for('edit_sequence', id=item.id)))
            fmt_string.append('<button onclick="seq_delete(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>' % (item.id))

        if item.draftable:
            fmt_string.append('<button onclick="seq_new_draft(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-duplicate"></span>&nbsp;</button>' % (item.id))
            fmt_string.append('<button onclick="seq_withdraw(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>' % (item.id))


        return ''.join(fmt_string)

def setup_sequence_list_table(results, current_user):
    table = make_GeneDescription_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
        item.draftable = item.can_draft(current_user)
    table.add_column('sequence_name', SequenceListActionCol('Sequence Name'))
    table._cols.move_to_end('sequence_name', last=False)
    return table

