# Composite tables for View Submission page - defined manually

import textile
from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField

from db.submission_db import *
from db.repertoire_db import *
from db.editable_table import *
from db.genotype_description_db import *
from db.inference_tool_db import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *
from db.notes_entry_db import *
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
        return Markup(textile.textile(item.body)) if item.parent is not None else "<strong>%s</strong><br>%s" % (item.title, Markup(textile.textile(item.body)))

class DelegateForm(FlaskForm):
    delegate = SelectField('Delegate', coerce=int)

class Delegate_table(StyledTable):
    id = Col("id", show=False)
    name = StyledCol("Name", tooltip="Delegate Name")
    address = StyledCol("Address", tooltip="Delegate Address")

def make_Delegate_table(results, private = False, classes=()):
    t=create_table(base=Delegate_table)
    ret = t(results, classes=classes)
    return ret

class EditableDelegateTable(EditableTable):
    def check_add_item(self, request, db):
        added = False
        if self.form.add_delegates.data:
            tagged = True
            try:
                user_id = self.form.delegate.data
                user = db.session.query(User).filter(User.id == user_id).one_or_none()
                sub = db.session.query(Submission).filter(Submission.id==self.sub_id).one_or_none()
                if user in sub.delegates:
                    raise ValueError('%s is already a delegate!' % user.name)
                sub.delegates.append(user)
                db.session.commit()
                added = True
            except ValueError as e:
                self.form.delegate.errors = list(self.form.delegate.errors) + [e]
        return (added, None, None)

    def process_deletes(self, db):
        tag = '%s_del_' % self.name
        for field in self.form._fields:
            if tag in field and self.form[field].data:
                for p in self.items:
                    if p['id'] == int(field.replace(tag, '')):
                        sub = db.session.query(Submission).filter(Submission.id==self.sub_id).one_or_none()
                        for user in sub.delegates:
                            if user.id == p['user_id']:
                                sub.delegates.remove(user)
                        db.session.commit()
                        return True
        return False



def setup_submission_view_forms_and_tables(sub, db, private):
    tables = {}
    tables['submission'] = make_Submission_view(sub, private)
    tables['ack'] = make_Acknowledgements_table(sub.acknowledgements)
    tables['repertoire'] = make_Repertoire_view(sub.repertoire[0])
    tables['pub'] = make_PubId_table(sub.repertoire[0].pub_ids)
    tables['fw_primer'] = make_ForwardPrimer_table(sub.repertoire[0].forward_primer_set)
    tables['rv_primer'] = make_ReversePrimer_table(sub.repertoire[0].reverse_primer_set)
    tables['submission_notes'] = make_NotesEntry_view(sub.notes_entries[0])

    if len(sub.repertoire) == 0:
        sub.repertoire.append(Repertoire())
        db.session.commit()

    if len(sub.notes_entries) == 0:
        sub.notes_entries.append(NotesEntry())
        db.session.commit()

    for item in tables['submission_notes'].items:
        if item['item'] == 'Notes':
            if item['value'] == '' or item['value'] is None:
                item['value'] = 'No notes provided'
            else:
                item['value'] = Markup(textile.textile(item['value']))

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
        replies = db.session.query(JournalEntry).filter_by(submission_id = sub.id, type = 'note', parent_id = thread.id).order_by(JournalEntry.date.asc()).all()
        replies= [thread] + replies
        t = StyledTable(replies, classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['notes'].append((thread.id, t))

    journal_entry_form = JournalEntryForm()
    hidden_return_form = HiddenReturnForm()

    delegates = []
    id = 1
    for user in sub.delegates:
        delegates.append({'id': id, 'name': user.name, 'address': user.address, 'user_id': user.id, 'sub_id': sub.id})
        id += 1
    tables['delegate_table'] = EditableDelegateTable(make_Delegate_table(delegates), 'delegates', DelegateForm, delegates, legend='Add Delegate')
    tables['delegate_table'].sub_id = sub.id

    users = db.session.query(User).filter(User.active==True, User.confirmed_at!=None)
    tables['delegate_table'].form.delegate.choices = [(user.id, '%s, %s' % (user.name, user.address)) for user in users]

    form = AggregateForm(journal_entry_form, hidden_return_form, tables['delegate_table'].form)
    return (form, tables)
