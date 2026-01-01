# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#



from db.germline_set_db import *
from db.journal_entry_db import *
from ogrdb.sequence.inferred_sequence_table import MessageHeaderCol, MessageBodyCol
from ogrdb.germline_set.germline_set_table import setup_gene_description_table
from ogrdb.submission.submission_edit_form import *
from textile_filter import safe_textile


class GermlineSetNotes_table(StyledTable):
    id = Col("id", show=False)
    notes = StyledCol("", tooltip="Notes", column_html_attrs={"class": "notes-table-row"})


def make_GermlineSetNotes_table(results, private = False, classes=()):
    t=create_table(base=GermlineSetNotes_table)
    ret = t(results, classes=classes)
    return ret




def setup_germline_set_view_tables(db, germline_set, private):
    tables = {}
    tables['description'] = make_GermlineSet_view(germline_set)
    tables['genes'] = setup_gene_description_table(germline_set, action=False)
    tables['acknowledgements'] = make_Acknowledgements_table(germline_set.acknowledgements)
    tables['publications'] = make_PubId_table(germline_set.pub_ids)
    tables['attachments'] = EditableAttachedFileTable(make_AttachedFile_table(germline_set.notes_entries[0].attached_files),
                                                      'attached_files', AttachedFileForm, germline_set.notes_entries[0].attached_files,
                                                      legend='Attachments',
                                                      delete=False,
                                                      download_route='download_germline_set_attachment')
    tables['attachments'].table.filename.name = 'Supplementary Files'

    history = db.session.query(JournalEntry).filter_by(germline_set_id = germline_set.id, type = 'history').all()
    tables['history'] = []

    for entry in history:
        t = StyledTable([entry], classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['history'].append(t)

    return tables
