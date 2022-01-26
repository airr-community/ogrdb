# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Composite tables for View Submission page - defined manually

from textile_filter import safe_textile

from db.repertoire_db import *
from db.editable_table import *
from db.genotype_description_db import *
from db.inference_tool_db import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *
from db.notes_entry_db import *
from db.primer_db import *
from db.gene_description_db import *
from db.attached_file_db import *

from ogrdb.submission.submission_edit_form import ToolNameCol, SeqNameCol, GenNameCol, SubjCol, EditableAttachedFileTable
from forms.journal_entry_form import JournalEntryForm
from forms.aggregate_form import AggregateForm
from forms.attached_file_form import *

class HiddenReturnForm(FlaskForm):
    type = StringField('Type')
    action = StringField('Type')


class MessageHeaderCol(StyledCol):
    def td_contents(self, item, attr_list):
        return "<strong>%s</strong><br><small>%s</small>" % (item.author, item.date)


class MessageBodyCol(StyledCol):
    def td_contents(self, item, attr_list):
        return Markup(safe_textile(item.body)) if item.parent is not None else "<strong>%s</strong><br>%s" % (item.title, Markup(safe_textile(item.body)))


class DelegateForm(FlaskForm):
    delegate = SelectField('Delegate', coerce=int)


class Delegate_table(StyledTable):
    id = Col("id", show=False)
    name = StyledCol("Name", tooltip="Delegate Name")
    address = StyledCol("Address", tooltip="Delegate Address")


def make_Delegate_table(results, private = False, classes=()):
    t=create_table(base=Delegate_table)
    ret = t(results, classes=classes, empty_message='No Delegates have been added')
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
                if user_id < 0:
                    raise ValueError('Please select a delegate to add.')
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


class PubGeneCol(StyledCol):
    def td_contents(self, item, attr_list):
        ret = ''
        for desc in item.gene_descriptions:
            if desc.status == 'published':
                ret = '<a href=%s>%s</a>' % (url_for('sequence', id=desc.id), desc.description_id)
                break
        return ret


class DraftGeneCol(StyledCol):
    def td_contents(self, item, attr_list):
        ret = ''
        for desc in item.gene_descriptions:
            if desc.status == 'draft':
                ret = '<a href=%s>%s</a>' % (url_for('edit_sequence', id=desc.id), desc.description_id)
                break
        return ret

class PubSequenceCol(StyledCol):
    def td_contents(self, item, attr_list):
        return('<a href="%s">%s</a>'  % (url_for('sequence', id=item['published_id']), item['published_name'])) if item['status'] == 'published' else ''

class DraftSequenceCol(StyledCol):
    def td_contents(self, item, attr_list):
        return('<a href="%s">%s</a>'  % (url_for('edit_sequence', id=item['published_id']), item['published_name'])) if item['status'] == 'draft' else ''

class MatchingSequencesTable(StyledTable):
    sequence_name = StyledCol("Sequence", tooltip="Name of inferred sequence as referred to in the submission")
    subject_id = StyledCol("Subject", tooltip="ID of the subject from which this sequence was inferred")
    genotype_name = StyledCol("Genotype", tooltip="Name of genotype from which sequence was drawn")
    draft_name = DraftSequenceCol("Draft", tooltip="Draft sequence matching this inference")
    published_name = PubSequenceCol("Published", tooltip="Published sequence matching this inference")
    match = StyledCol("Match", tooltip="Details of the match")

def make_MatchingSequences_table(results, classes=()):
    t=create_table(base=MatchingSequencesTable)
    ret = t(results, classes=classes)
    return ret

def setup_matching_sequences_table(sub):
    results = []
    our_descriptions = []
    for inf in sub.inferred_sequences:
        our_descriptions.extend(inf.gene_descriptions)

    for desc in sub.genotype_descriptions:
        for seq in desc.genotypes:
            for dup in seq.published_duplicates:
                if dup not in our_descriptions:
                    alignment = report_dupe(seq.nt_sequence, 'Sequence', seq.sequence, dup.description_id)
                    match = Markup('<button id="aln_view" name="aln_view" type="button" class="btn btn-xs %s icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon %s"></span>&nbsp;</button>' \
                                   % ('text-info', alignment, dup.description_id, format_fasta_sequence('Sequence', seq.nt_sequence, 50) + format_fasta_sequence(dup.description_id, dup.sequence, 50), 'glyphicon-search'))

                    results.append({'subject_id': seq.genotype_description.genotype_subject_id,
                                    'genotype_name': seq.genotype_description.genotype_name,
                                    'sequence_name': seq.sequence_id,
                                    'published_name': dup.description_id,
                                    'published_id': dup.id,
                                    'status': dup.status,
                                    'match': match})

    if len(results) == 0:
        return None

    table = make_MatchingSequences_table(results)
    return table


def setup_submission_view_forms_and_tables(sub, db, private):
    if len(sub.repertoire) == 0:
        sub.repertoire.append(Repertoire())
        db.session.commit()

    tables = {}
    tables['submission'] = make_Submission_view(sub, private)
    tables['ack'] = make_Acknowledgements_table(sub.acknowledgements)
    tables['repertoire'] = make_Repertoire_view(sub.repertoire[0])
    tables['pub'] = make_PubId_table(sub.repertoire[0].pub_ids)
    tables['submission_notes'] = make_NotesEntry_view(sub.notes_entries[0])
    tables['matches'] = setup_matching_sequences_table(sub) if private else None
    tables['attachments'] = EditableAttachedFileTable(make_AttachedFile_table(sub.notes_entries[0].attached_files), 'attached_files', AttachedFileForm, sub.notes_entries[0].attached_files, legend='Attachments', delete=False, download_route='download_submission_attachment')

    tables['primer_sets'] = []
    for primer_set in sub.repertoire[0].primer_sets:
        tables['primer_sets'].append((primer_set.primer_set_name, primer_set.primer_set_notes, make_Primer_table(primer_set.primers)))

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

    for item in tables['repertoire'].items:
        if item['item'] == 'Dataset URL' and item['value'] is not None and len(item['value']) > 0:
                item['value'] = Markup('<a href="%s">%s</a>' % (item['value'],item['value']))

    t = make_InferenceTool_table(sub.inference_tools)
    t.add_column('id', ActionCol("View", delete=False, view_route='inference_tool'))
    tables['inference_tool'] = t

    t = make_GenotypeDescription_table(sub.genotype_descriptions)
    t.add_column('toolname', ToolNameCol('Tool/Setting Name'))
    t.add_column('id', ActionCol("View", delete=False, view_route='genotype'))
    tables['genotype_description'] = t

    t = make_InferredSequence_table(sub.inferred_sequences)
    t.add_column('id', ActionCol("View", delete=False, view_route='inferred_sequence'))
    t.add_column('Sequence', SeqNameCol('Sequence'))
    t.add_column('Subject', SubjCol('Subject'))
    t.add_column('Genotype', GenNameCol('Genotype'))
    t.add_column('Published', PubGeneCol('Published'))
    tables['inferred_sequence'] = t

    t = make_InferredSequence_table(sub.inferred_sequences)
    t.add_column('id', ActionCol("View", delete=False, view_route='inferred_sequence'))
    t.add_column('Sequence', SeqNameCol('Sequence'))
    t.add_column('Subject', SubjCol('Subject'))
    t.add_column('Genotype', GenNameCol('Genotype'))
    t.add_column('Draft', DraftGeneCol('Draft'))
    t.add_column('Published', PubGeneCol('Published'))
    tables['iarc_inferred_sequence'] = t

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
    tables['delegate_table'].form.delegate.choices = [(-1, '--- Select User to add as Delegate ---')] + [(user.id, '%s, %s' % (user.name, user.address)) for user in users]

    form = AggregateForm(journal_entry_form, hidden_return_form, tables['delegate_table'].form)
    return (form, tables)
