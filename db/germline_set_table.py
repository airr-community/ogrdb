# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#
from db.attached_file_db import make_AttachedFile_table
from db.notes_entry_db import NotesEntry
from forms.attached_file_form import AttachedFileForm
from forms.submission_edit_form import EditableAckTable, EditableAttachedFileTable, EditablePubIdTable
from db.repertoire_db import make_Acknowledgements_table, make_PubId_table
from db.journal_entry_db import *
from forms.repertoire_form import AcknowledgementsForm, PubIdForm
from textile_filter import *
from flask import url_for
from db.gene_description_db import *
from db.inferred_sequence_table import MessageHeaderCol, MessageBodyCol



class GeneDescriptionTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = '<button type="button" class="del_gene_button btn btn-xs text-danger icon_back" data-sid="%s" data-gid="%s" id="del_gene_%s" data-toggle="tooltip" title="Delete"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>' % (item['set_id'], item['gene_id'], item['gene_id'])
        return(contents)


class DescLinkCol(StyledCol):
    def td_format(self, content):
        return Markup('<a href="%s">%s</span>&nbsp;</a>' % (url_for('sequence', id=content), content))


class GeneDescriptionTable(StyledTable):
    name = DescLinkCol("Gene Name")
    seq_id = StyledCol("Seq ID")
    imgt_name = StyledCol("IMGT Name")
    status = StyledCol("Status")


def make_GeneDescription_table(results, private = False, classes=()):
    t = create_table(base=GeneDescriptionTable)
    ret = t(results, classes=classes)
    return ret


def setup_gene_description_table(germline_set, action=True):
    results = []
    for gene_description in germline_set.gene_descriptions:
        desc = Markup('<a href="%s">%s</a>' % (url_for('sequence', id=gene_description.id), gene_description.sequence_name))
        results.append({
            'name': desc,
            'imgt_name': gene_description.imgt_name,
            'status': gene_description.status,
            'gene_id': gene_description.id,
            'set_id': germline_set.id,
            'seq_id': gene_description.coding_sequence_identifier})

    table = make_GeneDescription_table(results)

    if action:
        table.add_column('action', GeneDescriptionTableActionCol(''))
        table._cols.move_to_end('action', last=False)

    return table


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

