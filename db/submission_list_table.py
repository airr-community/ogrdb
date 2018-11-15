# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask import url_for
from copy import deepcopy

from db.styled_table import *
from db.submission_db import *

class SubmissionListActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        fmt_string = []

        if item.viewable:
            fmt_string.append('<a href="%s">%s</a>'  % (url_for('submission', id=item.submission_id), item.submission_id))
        else:
            fmt_string.append(item.submission_id)

        if item.editable:
            fmt_string.append('<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Edit"></span>&nbsp;</a>'  % (url_for('edit_submission', id=item.submission_id)))
            fmt_string.append('<button onclick="sub_delete(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span>&nbsp;</button>' % (item.submission_id))

        return ''.join(fmt_string)

def setup_submission_list_table(results, current_user):
    table = make_Submission_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
    table.add_column('submission_id', SubmissionListActionCol('submission_id'))
    return table

