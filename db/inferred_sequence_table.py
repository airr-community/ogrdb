from forms.submission_edit_form import EditableAckTable
from db.repertoire_db import make_Acknowledgements_table
from forms.repertoire_form import AcknowledgementsForm
from textile_filter import *

from db.styled_table import *
from db.gene_description_db import *

class InferredSequenceTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        return '<button type="button" class="delbutton btn btn-xs text-danger icon_back" data-id="%s" data-inf="%s" id="%s_%s"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>' % (item['id'], item['sequence_id'], item['id'], item['sequence_id'])


class InferredSequenceTable(StyledTable):
    submission_id = StyledCol("Submission ID", tooltip="Submission ID from which this inference was taken")
    sequence_name = StyledCol("Sequence Name", tooltip="Name of inferred sequence in submission")

def make_InferredSequence_table(results, private = False, classes=()):
    t=create_table(base=InferredSequenceTable)
    ret = t(results, classes=classes)
    return ret

class MessageHeaderCol(StyledCol):
    def td_contents(self, item, attr_list):
        return "<strong>%s</strong><br><small>%s</small>" % (item.author, item.date)

class MessageBodyCol(StyledCol):
    def td_contents(self, item, attr_list):
        return Markup(textile.textile(item.body)) if item.parent is not None else "<strong>%s</strong><br>%s" % (item.title, Markup(textile.textile(item.body)))

def setup_inferred_sequence_table(seqs, id):
    results = []
    for seq in seqs:
        results.append({'submission_id': seq.submission.submission_id, 'sequence_name': seq.sequence_details.sequence_id, 'id': id, 'sequence_id': seq.id})
    table = make_InferredSequence_table(results)
    table.add_column('action', InferredSequenceTableActionCol(''))
    table._cols.move_to_end('action', last=False)
    foo = table.__html__()
    return table

def setup_sequence_edit_tables(seq):
    tables = {}
    tables['inferred_sequence'] = setup_inferred_sequence_table(seq.inferred_sequences, seq.id)
    tables['ack'] = EditableAckTable(make_Acknowledgements_table(seq.acknowledgements), 'ack', AcknowledgementsForm, seq.acknowledgements, legend='Add Acknowledgement')

    history = db.session.query(JournalEntry).filter_by(gene_description_id = seq.id, type = 'history').all()
    tables['history'] = []

    for entry in history:
        t = StyledTable([entry], classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['history'].append(t)

    return tables

