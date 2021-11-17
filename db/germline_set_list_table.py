# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask import url_for
from copy import deepcopy
from imgt.imgt_ref import get_imgt_config
from db.styled_table import *
from db.germline_set_db import *

class GermlineSetListActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        fmt_string = []

        if item.viewable:
            fmt_string.append('<a href="%s">%s</a>' % (url_for('germline_set', id=item.id), item.germline_set_name))
        else:
            fmt_string.append(item.germline_set_name)

        if item.editable:
            fmt_string.append('<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Edit"></span>&nbsp;</a>'  % (url_for('edit_germline_set', id=item.id)))
            fmt_string.append('<button onclick="set_delete(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span>&nbsp;</button>' % (item.id))

        if item.draftable:
            fmt_string.append('<button onclick="set_new_draft(this.id)" class="btn btn-xs text-warning icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-duplicate" data-toggle="tooltip" title="Create Draft"></span></button>' % (item.id))
            fmt_string.append('<button onclick="set_withdraw(this.id)" class="btn btn-xs text-danger icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span></button>' % (item.id))

        return ''.join(fmt_string)


class GermlineSetListDownloadCol(StyledCol):
    def td_contents(self, item, attr_list):
        fmt_string = []
        fmt_string.append(
            '<a href="%s" class="btn btn-xs text-primary icon_back"><span class="glyphicon glyphicon-file" data-toggle="tooltip" title="AIRR (JSON)"></span>&nbsp;</a>' %
            url_for('download_germline_set', set_id=item.id, format='airr'))
        fmt_string.append(
            '<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-file" data-toggle="tooltip" title="FASTA Gapped"></span>&nbsp;</a>' %
            url_for('download_germline_set', set_id=item.id, format='gapped'))
        fmt_string.append(
            '<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-file" data-toggle="tooltip" title="FASTA Ungapped"></span>&nbsp;</a>' %
            url_for('download_germline_set', set_id=item.id, format='ungapped'))

        for af in item.notes_entries[0].attached_files:
            fmt_string.append(
                '<a href="%s" class="btn btn-xs text-muted icon_back"><span class="glyphicon glyphicon-file" data-toggle="tooltip" title="%s"></span>&nbsp;</a>' %
                (url_for('download_germline_set_attachment', id=af.id), af.filename))

        return ''.join(fmt_string)


def setup_germline_set_list_table(results, current_user):
    table = make_GermlineSet_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
        item.draftable = item.can_draft(current_user)

    table.add_column('set_name', GermlineSetListActionCol('Set Name'))
    table._cols.move_to_end('set_name', last=False)
    return table


def setup_published_germline_set_list_table(results, current_user):
    table = make_GermlineSet_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
        item.draftable = item.can_draft(current_user)

    table.add_column('download', GermlineSetListDownloadCol('Downloads'))
    table._cols.move_to_end('download', last=False)

    table.add_column('set_name', GermlineSetListActionCol('Set Name'))
    table._cols.move_to_end('set_name', last=False)
    del table._cols['locus']
    return table

