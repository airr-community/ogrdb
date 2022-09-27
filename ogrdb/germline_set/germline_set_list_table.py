# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#
from operator import attrgetter

from flask import url_for
from db.germline_set_db import *


def make_germline_action_string(item):
    fmt_string = []

    if item.viewable:
        fmt_string.append('<a href="%s">%s</a>' % (url_for('germline_set', id=item.id), item.germline_set_name))
    else:
        fmt_string.append(item.germline_set_name)

    if item.editable:
        fmt_string.append(
            '<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Edit"></span>&nbsp;</a>' % (
                url_for('edit_germline_set', id=item.id)))
        fmt_string.append(
            '<button onclick="set_delete(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span>&nbsp;</button>' % (
                item.id))
    if item.draftable:
        fmt_string.append(
            '<button onclick="set_new_draft(this.id)" class="btn btn-xs text-warning icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-duplicate" data-toggle="tooltip" title="Create Draft"></span></button>' % (
                item.id))
        fmt_string.append(
            '<button onclick="set_withdraw(this.id)" class="btn btn-xs text-danger icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span></button>' % (
                item.id))
    if item.zenodo_updateable:
        fmt_string.append(
            '<button onclick="set_update_doi(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-cloud-upload" data-toggle="tooltip" title="Update doi"></span>&nbsp;</button>' % (
                item.id))
    if item.zenodo_createable:
        fmt_string.append(
            '<button onclick="set_create_doi(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-tower" data-toggle="tooltip" title="Create doi"></span>&nbsp;</button>' % (
                item.id))
    return ''.join(fmt_string)


def make_download_items(item):
    fmt_string = []
    fmt_string.append(
        '<a href="%s" class="btn btn-xs text-primary icon_back"><span class="glyphicon glyphicon-file"></span>&nbsp;AIRR (JSON)</a>' %
        url_for('download_germline_set', set_id=item.id, format='airr'))
    fmt_string.append(
        '<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-file"></span>&nbsp;FASTA Gapped</a>' %
        url_for('download_germline_set', set_id=item.id, format='gapped'))
    fmt_string.append(
        '<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-file"></span>&nbsp;FASTA Ungapped</a>' %
        url_for('download_germline_set', set_id=item.id, format='ungapped'))
    for af in item.notes_entries[0].attached_files:
        fmt_string.append(
            '<a href="%s" class="btn btn-xs text-muted icon_back"><span class="glyphicon glyphicon-file""></span>&nbsp;%s</a>' %
            (url_for('download_germline_set_attachment', id=af.id), af.filename))
    return fmt_string


class GermlineSetListNamedActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        return make_germline_action_string(item)

class GermlineSetListDownloadCol(StyledCol):
    def td_contents(self, item, attr_list):
        return make_download_items(item)

class GermlineSetListDoiCol(StyledCol):
    def td_contents(self, item, attr_list):
        if item.doi and len(item.doi) > 0:
            return '<a href="https://doi.org/%s"><img src="https://zenodo.org/badge/DOI/%s.svg" alt="DOI"></a>' % (item.doi, item.doi)
        else:
            return ''


def setup_germline_set_list_table(results, current_user):
    table = make_GermlineSet_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
        item.draftable = item.can_draft(current_user)
        item.zenodo_createable = False
        item.zenodo_updateable = False

    table.add_column('set_name', GermlineSetListNamedActionCol('Set Name'))
    table._cols.move_to_end('set_name', last=False)
    return table


def setup_published_germline_set_list_info(results, current_user):
    affirmed = make_GermlineSet_table(results)
    del affirmed._cols['species']
    affirmed.add_column('download', GermlineSetListDownloadCol('Download'))

    add_actions = False
    for item in affirmed.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
        item.draftable = item.can_draft(current_user)
        item.zenodo_createable = item.draftable and (item.zenodo_base_deposition is None or len(item.zenodo_base_deposition) == 0)
        item.zenodo_updateable = item.draftable and (not item.zenodo_createable) and (item.zenodo_current_deposition is None or len(item.zenodo_current_deposition) == 0)

    affirmed.add_column('set_name', GermlineSetListNamedActionCol('Set Name'))
    affirmed._cols.move_to_end('set_name', last=False)

    # remove subgroup if all entries are blank

    keep_subgroup = False

    for row in affirmed.items:
        if row.species_subgroup and len(row.species_subgroup) > 0:
            keep_subgroup = True
            break

    if not keep_subgroup:
        del affirmed._cols['species_subgroup']

    del affirmed._cols['doi']
    affirmed.add_column('DOI', GermlineSetListDoiCol('DOI'))

    affirmed.table_id = 'affirmed_table'

    return affirmed

