# Composite tables for View Submission page - defined manually

from flask_wtf import FlaskForm
from wtforms import StringField

from db.submission_db import *
from db.repertoire_db import *
from db.editable_table import *
from db.genotype_description_db import *
from db.inference_tool_db import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *
from forms.submission_edit_form import ToolNameCol, SeqNameCol, GenNameCol
from forms.journal_entry_form import JournalEntryForm
from forms.aggregate_form import AggregateForm

class HiddenReturnForm(FlaskForm):
    type = StringField('Type')
    action = StringField('Type')

class MessageHeaderCol(StyledCol):
    def td_contents(self, item, attr_list):
        return "<strong>%s</strong><br><small>%s</small>" % (item.author, item.date)

class MessageBodyCol(StyledCol):
    def td_contents(self, item, attr_list):
        return item.body if item.parent is not None else "<strong>%s</strong><br>%s" % (item.title, item.body)


def setup_submission_view_forms_and_tables(sub, db, private):
    tables = {}
    tables['submission'] = make_Submission_view(sub, private)
    tables['ack'] = make_Acknowledgements_table(sub.acknowledgements)
    tables['repertoire'] = make_Repertoire_view(sub.repertoire[0])
    tables['pub'] = make_PubId_table(sub.repertoire[0].pub_ids)
    tables['fw_primer'] = make_ForwardPrimer_table(sub.repertoire[0].forward_primer_set)
    tables['rv_primer'] = make_ReversePrimer_table(sub.repertoire[0].reverse_primer_set)

    t = make_InferenceTool_table(sub.inference_tools)
    t.add_column('id', ActionCol("View", delete=False, view_route='inference_tool'))
    tables['inference_tool'] = t

    t = make_GenotypeDescription_table(sub.genotype_descriptions)
    t.add_column('toolname', ToolNameCol('Tool/Setting Name'))
    t.add_column('id', ActionCol("View", delete=False, view_route='genotype'))
    tables['genotype_description'] = t

    t = make_InferredSequence_table(sub.inferred_sequences)
    t2 = make_InferredSequence_table(sub.inferred_sequences)
    t3 = make_InferredSequence_table(sub.inferred_sequences)
    t.add_column('Sequence', SeqNameCol('Sequence'))
    t.add_column('Genotype', GenNameCol('Genotype'))
    tables['inferred_sequence'] = t

    history = db.session.query(JournalEntry).filter_by(submission_id = sub.id, type = 'history').all()
    t = make_JournalEntry_table(history)
    tables['history'] = t

    tables['notes'] = []
    threads = db.session.query(JournalEntry).filter_by(submission_id = sub.id, type = 'note', parent_id = None).order_by(JournalEntry.date.desc()).all()
    for thread in threads:
        replies = db.session.query(JournalEntry).filter_by(submission_id = sub.id, type = 'note', parent_id = thread.id).order_by(JournalEntry.date.desc()).all()
        replies= [thread] + replies
        t = StyledTable(replies, classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['notes'].append((thread.id, t))

    journal_entry_form = JournalEntryForm()
    hidden_return_form = HiddenReturnForm()
    form = AggregateForm(journal_entry_form, hidden_return_form)

    return (form, tables)
