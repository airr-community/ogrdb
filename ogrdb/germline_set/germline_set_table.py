# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#
from db.attached_file_db import make_AttachedFile_table
from db.germline_set_db import GermlineSet
from forms.attached_file_form import AttachedFileForm
from ogrdb.submission.submission_edit_form import EditableAckTable, EditableAttachedFileTable, EditablePubIdTable
from db.repertoire_db import make_Acknowledgements_table, make_PubId_table
from db.journal_entry_db import *
from forms.repertoire_form import AcknowledgementsForm, PubIdForm
from textile_filter import *
from flask import url_for
from db.gene_description_db import *
from ogrdb.sequence.inferred_sequence_table import MessageHeaderCol, MessageBodyCol
from operator import attrgetter


class GeneDescriptionTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = '<button type="button" class="del_gene_button btn btn-xs text-danger icon_back" data-sid="%s" data-gid="%s" id="del_gene_%s" data-toggle="tooltip" title="Delete"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>' % (item['set_id'], item['gene_id'], item['gene_id'])
        return(contents)


class DescLinkCol(StyledCol):
    def td_format(self, content):
        return Markup('<a href="%s">%s</span>&nbsp;</a>' % (url_for('sequence', id=content), content))


class GeneDescriptionTable(StyledTable):
    name = DescLinkCol("Label")
    version = StyledCol("Vn")
    date = StyledDateCol("Date")
    imgt_name = StyledCol("IMGT Name")
    alt_names = StyledCol("Alt Names")
    functionality = StyledCol('Functionality')
    subgroup = StyledCol("Subgrp")
    status = StyledCol("Status")
    sequence = HiddenCol("Sequence")
    sequence_gapped = HiddenCol("Gapped Sequence")


def make_GeneDescription_table(results, private=False, classes=()):
    t = create_table(base=GeneDescriptionTable)
    ret = t(results, classes=classes)
    return ret


def setup_gene_description_table(germline_set, action=True):
    results = []
    for gene_description in germline_set.gene_descriptions:
        desc = Markup('<a href="%s">%s</a>' % (url_for('sequence', id=gene_description.id), gene_description.sequence_name))
        results.append({
            'name': desc,
            'raw_name': gene_description.sequence_name,
            'imgt_name': gene_description.imgt_name,
            'alt_names': gene_description.alt_names,
            'functionality': gene_description.functionality,
            'version': gene_description.release_version,
            'date': gene_description.release_date,
            'status': gene_description.status,
            'subgroup': gene_description.species_subgroup,
            'sequence': gene_description.sequence,
            'sequence_gapped': gene_description.coding_seq_imgt,
            'gene_id': gene_description.id,
            'set_id': germline_set.id})

    results.sort(key=lambda res: res['raw_name'].upper())
    table = make_GeneDescription_table(results)

    if action:
        table.add_column('action', GeneDescriptionTableActionCol(''))
        table._cols.move_to_end('action', last=False)
    else:
        del table._cols['status']

    return table

def list_germline_set_changes(germline_set):
    if germline_set.status == 'draft':
        prev = db.session.query(GermlineSet).filter(GermlineSet.germline_set_id == germline_set.germline_set_id, GermlineSet.status == 'published').one_or_none()

        if prev is None:
            prevs = db.session.query(GermlineSet).filter(GermlineSet.germline_set_id == germline_set.germline_set_id, GermlineSet.status == 'superceded').all()

            if len(prevs) > 0:
                prev = sorted(prevs, key=attrgetter('release_version'), reverse=True)[0]
    else:
        prev = None
        prevs = db.session.query(GermlineSet).filter(GermlineSet.germline_set_id == germline_set.germline_set_id, GermlineSet.status.in_(['published', 'superceded']))\
            .filter(GermlineSet.release_version < germline_set.release_version)\
            .all()

        if len(prevs) > 0:
            prev = sorted(prevs, key=attrgetter('release_version'), reverse=True)[0]

    if prev is None:
        return ''

    current_descs = {}
    for desc in germline_set.gene_descriptions:
        current_descs[desc.description_id] = desc

    prev_descs = {}
    for desc in prev.gene_descriptions:
        prev_descs[desc.description_id] = desc

    added = []
    removed = []
    changed = []

    for gid, prev_desc in prev_descs.items():
        if gid not in current_descs.keys():
            removed.append('<a href="%s">%s</a>' % (url_for('sequence', id=prev_descs[gid].id), prev_descs[gid].sequence_name))

    for gid, current_desc in current_descs.items():
        if gid not in prev_descs.keys():
            added.append('<a href="%s">%s</a>' % (url_for('sequence', id=current_desc.id), current_desc.sequence_name))

    for gid, current_desc in current_descs.items():
        if gid in prev_descs.keys() and current_desc.id != prev_descs[gid].id:
            if current_desc.coding_seq_imgt == prev_descs[gid].coding_seq_imgt:
                changed.append('<a href="%s">%s</a>: v%d->%s' % (
                    url_for('sequence', id=current_desc.id),
                    current_desc.sequence_name,
                    prev_descs[gid].release_version,
                    'v%d' % current_desc.release_version if current_desc.status != 'draft' else 'draft',
                ))
            else:
                changed.append('<a href="%s">%s</a>: v%d->%s, sequence changed' % (
                    url_for('sequence', id=current_desc.id),
                    current_desc.sequence_name,
                    prev_descs[gid].release_version,
                    'v%d' % current_desc.release_version if current_desc.status != 'draft' else 'draft'
                ))

    history = []

    if len(added) > 0:
        history.append(Markup('<b>Added</b><br>' + ','.join(added)))

    if len(removed) > 0:
        history.append(Markup('<b>Removed</b><br>' + ','.join(removed)))

    if len(changed) > 0:
        history.append(Markup('<b>Changed</b><br>' + '<br>'.join(changed)))

    if len(history) > 0:
        return Markup('<br>'.join(history))

    return ''


def setup_germline_set_edit_tables(db, germline_set):
    tables = {}

    tables['genes'] = setup_gene_description_table(germline_set)
    tables['ack'] = EditableAckTable(make_Acknowledgements_table(germline_set.acknowledgements), 'ack', AcknowledgementsForm, germline_set.acknowledgements, legend='Add Acknowledgement')
    tables['attachments'] = EditableAttachedFileTable(make_AttachedFile_table(germline_set.notes_entries[0].attached_files),
                                                      'attached_files', AttachedFileForm, germline_set.notes_entries[0].attached_files,
                                                      legend='Attachments',
                                                      delete_route='delete_germline_set_attachment',
                                                      delete_message='Are you sure you wish to delete the attachment?',
                                                      download_route='download_germline_set_attachment')
    tables['pubmed_table'] = EditablePubIdTable(make_PubId_table(germline_set.pub_ids), 'pubmed', PubIdForm, germline_set.pub_ids, legend='Add Publication')

    history = db.session.query(JournalEntry).filter_by(germline_set_id = germline_set.id, type ='history').all()
    tables['history'] = []

    for entry in history:
        t = StyledTable([entry], classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['history'].append(t)

    return tables

