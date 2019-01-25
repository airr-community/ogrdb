# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Composite form for Edit Submission page - defined manually

from db.repertoire_db import *
from db.misc_db import *
from db.inference_tool_db import *
from db.genotype_description_db import *
from db.editable_table import *
from db.inferred_sequence_db import *
from db.notes_entry_db import *
from db.primer_set_db import *
from forms.repertoire_form import *
from forms.submission_form import *
from forms.inference_tool_form import *
from forms.genotype_description_form import *
from forms.aggregate_form import *
from forms.inferred_sequence_form import *
from forms.notes_entry_form import *
from forms.primer_set_form import *
from sys import exc_info
from get_ncbi_details import *
from collections import namedtuple
from custom_validators import ValidNucleotideSequence, ValidOrcidID
from wtforms import HiddenField, SelectField

class EditablePubIdTable(EditableTable):
    def check_add_item(self, request, db):
        added = False
        if self.form.add_pubmed.data:
            tagged = True
            try:
                if self.form.pubmed_id.data in [i.pubmed_id for i in self.items]:
                    raise ValueError('That publication is already in the table')
                res = get_pmid_details( self.form.pubmed_id.data)
                p = PubId()
                p.pub_title = res['title']
                p.pub_authors = res['authors']
                p.pubmed_id = request.form['pubmed_id']
                self.items.append(p)
                self.table = make_PubId_table(self.items)
                self.form.pubmed_id.data = ''
                db.session.commit()
                added = True
            except ValueError as e:
                self.form.pubmed_id.errors = list(self.form.pubmed_id.errors) + [e]
        return (added, None, None)

class EditablePrimerSetTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_primer_sets.data:
            try:
                p = PrimerSet()
                p.primer_set_name = ''
                p.primer_set_notes = ''
                self.items.append(p)
                self.table = make_PrimerSet_table(self.items)
                db.session.commit()
                return (True, 'primer_sets', p.id)
            except ValueError as e:
                self.form.primer_set_name.errors = list(self.form.primer_set_name.errors) + [e]
        return (False, None, None)

class EditableAckTable(EditableTable):
    def check_add_item(self, request, db):
        added = False
        if self.form.add_ack.data:
            try:
                if len(self.form.ack_name.data) < 1:
                    self.form.ack_name.errors = ['Name cannot be blank.']
                    raise ValueError()
                if len(self.form.ack_institution_name.data) < 1:
                    self.form.ack_institution_name.errors = ['Institution cannot be blank.']
                    raise ValueError()
                if len(self.form.ack_ORCID_id.data) > 0:
                    v = ValidOrcidID()
                    try:
                        v.__call__(self.form, self.form.ack_ORCID_id)
                    except ValidationError:
                        self.form.ack_ORCID_id.errors = ['Invalid ORCID ID.']
                        raise ValueError()

                for item in self.items:
                    if self.form.ack_name.data == item.ack_name and self.form.ack_institution_name.data == item.ack_institution_name:
                        self.form.ack_name.errors = ['That person is already in the table..']
                        raise ValueError()

                a = Acknowledgements()
                a.ack_name = self.form.ack_name.data
                a.ack_institution_name = self.form.ack_institution_name.data
                a.ack_ORCID_id = self.form.ack_ORCID_id.data
                self.items.append(a)
                self.table = make_Acknowledgements_table(self.items)
                db.session.commit()
                added = True
            except ValueError as e:
                pass

        return (added, None, None)

class EditableInferenceToolTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_tools.data:
            t = InferenceTool()
            t.tool_name = ''
            t.tool_settings_name = ''
            self.items.append(t)
            self.table = make_Acknowledgements_table(self.items)
            db.session.commit()
            return (True, 'edit_tool', t.id)
        return (False, None, None)


class ToolNameCol(StyledCol):
    def td_contents(self, item, attr_list):
        return self.td_format(item.inference_tool.tool_settings_name if item.inference_tool else '')

class EditableGenotypeDescriptionTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_genotype_description.data:
            d = GenotypeDescription()
            d.genotype_name = ''
            self.items.append(d)
            self.table = make_GenotypeDescription_table(self.items)
            db.session.commit()
            return (True, 'edit_genotype_description', d.id)
        return (False, None, None)

    def prep_table(self):
        self.table.add_column('Tool Setting', ToolNameCol('tool_settings'))
        return

class SeqNameCol(StyledCol):
    def td_contents(self, item, attr_list):
        ret = ''
        if item.sequence_details:
            ret += '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View Sequence"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>&nbsp;' \
                    % (format_nuc_sequence(item.sequence_details.nt_sequence, 50), item.sequence_details.sequence_id, format_fasta_sequence(item.sequence_details.sequence_id, item.sequence_details.nt_sequence, 50))
            ret += item.sequence_details.sequence_id

        return ret

class GenNameCol(StyledCol):
    def td_contents(self, item, attr_list):
        return self.td_format(item.genotype_description.genotype_name if item.genotype_description else '')

class SubjCol(StyledCol):
    def td_contents(self, item, attr_list):
        return self.td_format(item.genotype_description.genotype_subject_id if item.genotype_description.genotype_subject_id else '')

class EditableInferredSequenceTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_inferred_sequence.data:
            i = InferredSequence()
            i.sequence_id = None
            self.items.append(i)
            self.table = make_InferredSequence_table(self.items)
            db.session.commit()
            return (True, 'edit_inferred_sequence', i.id)
        return (False, None, None)

    def prep_table(self):
        self.table.add_column('Sequence', SeqNameCol('Sequence'))
        self.table.add_column('Genotype', GenNameCol('Genotype'))

def process_table_updates(tables, request, db):
    validation_result = ValidationResult()
    for table in tables.values():
        validation_result.tag = table.name
        (validation_result.added, validation_result.route, validation_result.id) = table.check_add_item(request, db)
        if validation_result.added:
            break
        if table.process_deletes(db):
            break
        for field in table.form:
            if len(field.errors) > 0:
                validation_result.valid = False
                break
        if not validation_result.valid:
            break

        validation_result.tag = None

    return validation_result


# Hidden fields to retain form state
class HiddenSubFieldsForm(FlaskForm):
    current_tab = HiddenField('Tab')

# Selector for repo
class RepoSelectorForm(FlaskForm):
    repository_select = SelectField("Repository", choices=[('NCBI SRA', 'NCBI SRA'), ('Other', 'Other')])


# Validation and completion of NCBI repository data
def update_sra_rep_details(form):
    if form.repository_select.data != 'NCBI SRA':
        return

    form.repository_name.data = 'NCBI SRA'

    if form.rep_accession_no.data[:5] != 'PRJNA':
        form.rep_accession_no.errors = ['Please provide the Bioproject id, eg PRJNA349143']
        raise ValueError()

    try:
        details = get_nih_project_details(form.rep_accession_no.data)
    except ValueError as e:
        form.rep_accession_no.errors = [e.args[0]]
        raise ValueError()

    form.rep_title.data = details['title']
    form.dataset_url.data = details['url']


def setup_submission_edit_forms_and_tables(sub, db):
    tables = {}

    if len(sub.repertoire) == 0:
        sub.repertoire.append(Repertoire())
        db.session.commit()

    if len(sub.notes_entries) == 0:
        sub.notes_entries.append(NotesEntry())
        db.session.commit()

    submission_form = SubmissionForm(obj = sub)
    species = db.session.query(Committee.species).all()
    submission_form.species.choices = [(s[0],s[0]) for s in species]

    repertoire_form = RepertoireForm(obj = sub.repertoire[0])
    notes_entry_form = NotesEntryForm(obj = sub.notes_entries[0])

    hidden_fields_form = HiddenSubFieldsForm()

    repo_selector_form = RepoSelectorForm()

    # Remove tool, genotype and inferred sequence entries that have no names. These are new entries that the user backed out of,
    # either by pressing cancel or by navigating away from the edit page.

    for tool in sub.inference_tools:
        if tool.tool_name == '':
            sub.inference_tools.remove(tool)

    for genotype in sub.genotype_descriptions:
        if genotype.genotype_name == '':
            sub.genotype_descriptions.remove(genotype)

    for seq in sub.inferred_sequences:
        if seq.sequence_id is None:
            sub.inferred_sequences.remove(seq)

    db.session.commit()

    tables['pubmed_table'] = EditablePubIdTable(make_PubId_table(sub.repertoire[0].pub_ids), 'pubmed', PubIdForm, sub.repertoire[0].pub_ids, legend='Add Publication')
    tables['primer_sets'] = EditablePrimerSetTable(make_PrimerSet_table(sub.repertoire[0].primer_sets), 'primer_sets', FlaskForm, sub.repertoire[0].primer_sets, legend='Add Primer Set', edit_route='primer_sets')
    tables['ack'] = EditableAckTable(make_Acknowledgements_table(sub.acknowledgements), 'ack', AcknowledgementsForm, sub.acknowledgements, legend='Add Acknowledgement')
    tables['tools'] = EditableInferenceToolTable(make_InferenceTool_table(sub.inference_tools), 'tools', InferenceToolForm, sub.inference_tools, legend='Add Tool and Settings', edit_route='edit_tool', delete_route='delete_tool', delete_message='Are you sure you wish to delete the tool settings and any associated genotypes?')
    tables['genotype_description'] = EditableGenotypeDescriptionTable(make_GenotypeDescription_table(sub.genotype_descriptions), 'genotype_description', GenotypeDescriptionForm, sub.genotype_descriptions, legend='Add Genotype', edit_route='edit_genotype_description', view_route='genotype_e', delete_route='delete_genotype', delete_message='Are you sure you wish to delete the genotype and all associated information?')
    tables['inferred_sequence'] = EditableInferredSequenceTable(make_InferredSequence_table(sub.inferred_sequences), 'inferred_sequence', InferredSequenceForm, sub.inferred_sequences, legend='Add Inferred Sequence', edit_route='edit_inferred_sequence')

    form = AggregateForm(submission_form, repertoire_form, notes_entry_form, tables['pubmed_table'].form, tables['primer_sets'].form, tables['ack'].form, tables['tools'].form,
                         tables['genotype_description'].form, tables['inferred_sequence'].form, hidden_fields_form, repo_selector_form)

    return (tables, form)




