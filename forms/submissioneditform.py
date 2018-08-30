# Composite form for Edit Submission page - defined manually

from db.repertoiredb import *
from db.miscdb import *
from db.inference_tool_db import *
from db.genotype_description_db import *
from db.editable_table import *
from db.inferred_sequence_db import *
from forms.repertoireform import *
from forms.submissionform import *
from forms.inference_tool_form import *
from forms.genotype_description_form import *
from forms.aggregate_form import *
from forms.inferred_sequence_form import *
from sys import exc_info
from get_pmid_details import get_pmid_details

class AggregateForm(FlaskForm):
    def __init__(self, *args):
        super().__init__()
        self.subforms = []

        for form in args:
            self.subforms.append(form)
            self._fields.update(form._fields)

    def __getattr__(self, attr):
        for form in self.subforms:
            a = getattr(form, attr, None)
            if a is not None: return a
        raise(AttributeError())

class EditablePubIdTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_pubmed.data:
            try:
                res = get_pmid_details(request.form['pubmed_id'])
                p = PubId()
                p.pub_title = res['title']
                p.pub_authors = res['authors']
                p.pubmed_id = request.form['pubmed_id']
                self.items.append(p)
                self.table = make_PubId_table(self.items)
                self.form.pubmed_id.data = ''
                db.session.commit()
                return (True, None, None)
            except ValueError as e:
                exc_value = exc_info()[1]
                self.form.pubmed_id.errors.append(exc_value.args[0])
        return (False, None, None)

class EditableFwPrimerTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_fw_primer.data:
            valid = True
            if len(self.form.fw_primer_name.data) < 1:
                self.form.fw_primer_name.errors.append('Name cannot be blank.')
                valid = False
            if len(self.form.fw_primer_seq.data) < 1:
                self.form.fw_primer_seq.errors.append('Sequence cannot be blank.')
                valid = False

            if valid:
                p = ForwardPrimer()
                p.fw_primer_name = self.form.fw_primer_name.data
                p.fw_primer_seq = self.form.fw_primer_seq.data
                self.items.append(p)
                self.table = make_ForwardPrimer_table(self.items)
                db.session.commit()
                return (True, None, None)
        return (False, None, None)

class EditableRvPrimerTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_rv_primer.data:
            valid = True
            if len(self.form.rv_primer_name.data) < 1:
                self.form.rv_primer_name.errors.append('Name cannot be blank.')
                valid = False
            if len(self.form.rv_primer_seq.data) < 1:
                self.form.rv_primer_seq.errors.append('Sequence cannot be blank.')
                valid = False

            if valid:
                p = ReversePrimer()
                p.rv_primer_name = self.form.rv_primer_name.data
                p.rv_primer_seq = self.form.rv_primer_seq.data
                self.items.append(p)
                self.table = make_ReversePrimer_table(self.items)
                db.session.commit()
                return (True, None, None)
        return (False, None, None)

class EditableAckTable(EditableTable):
    def check_add_item(self, request, db):
        if self.form.add_ack.data:
            valid = True
            if len(self.form.ack_name.data) < 1:
                self.form.ack_name.errors.append('Name cannot be blank.')
                valid = False
            if len(self.form.ack_institution_name.data) < 1:
                self.form.ack_institution_name.errors.append('Institution cannot be blank.')
                valid = False

            if valid:
                a = Acknowledgements()
                a.ack_name = self.form.ack_name.data
                a.ack_institution_name = self.form.ack_institution_name.data
                a.ack_ORCID_id = self.form.ack_ORCID_id.data
                self.items.append(a)
                self.table = make_Acknowledgements_table(self.items)
                db.session.commit()
                return (True, None, None)
        return (False, None, None)

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
            ret += '<button type="button" class="btn btn-xs btn-info" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>&nbsp;' \
                    % (format_nuc_sequence(item.sequence_details.nt_sequence, 50), item.sequence_details.sequence_id, format_fasta_sequence(item.sequence_details.sequence_id, item.sequence_details.nt_sequence, 50))
            ret += item.sequence_details.sequence_id

        return ret

class GenNameCol(StyledCol):
    def td_contents(self, item, attr_list):
        return self.td_format(item.genotype_description.genotype_name if item.genotype_description else '')

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


def setup_submission_edit_forms_and_tables(sub, db):
    tables = {}

    if len(sub.repertoire) == 0:
        sub.repertoire.append(Repertoire())
        db.session.commit()

    submission_form = SubmissionForm(obj = sub)
    species = db.session.query(Committee.species).all()
    submission_form.species.choices = [(s[0],s[0]) for s in species]

    repertoire_form = RepertoireForm(obj = sub.repertoire)

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
    tables['fw_primer'] = EditableFwPrimerTable(make_ForwardPrimer_table(sub.repertoire[0].forward_primer_set), 'fw_primer', ForwardPrimerForm, sub.repertoire[0].forward_primer_set, legend='Add Primer')
    tables['rv_primer'] = EditableRvPrimerTable(make_ReversePrimer_table(sub.repertoire[0].reverse_primer_set), 'rv_primer', ReversePrimerForm, sub.repertoire[0].reverse_primer_set, legend='Add Primer')
    tables['ack'] = EditableAckTable(make_Acknowledgements_table(sub.acknowledgements), 'ack', AcknowledgementsForm, sub.acknowledgements, legend='Add Acknowledgement')
    tables['tools'] = EditableInferenceToolTable(make_InferenceTool_table(sub.inference_tools), 'tools', InferenceToolForm, sub.inference_tools, legend='Add Tool and Settings', edit_route='edit_tool')
    tables['genotype_description'] = EditableGenotypeDescriptionTable(make_GenotypeDescription_table(sub.genotype_descriptions), 'genotype_description', GenotypeDescriptionForm, sub.genotype_descriptions, legend='Add Genotype', edit_route='edit_genotype_description', view_route='genotype')
    tables['inferred_sequence'] = EditableInferredSequenceTable(make_InferredSequence_table(sub.inferred_sequences), 'inferred_sequence', InferredSequenceForm, sub.inferred_sequences, legend='Add Inferred Sequence', edit_route='edit_inferred_sequence')

    form = AggregateForm(submission_form, repertoire_form, tables['pubmed_table'].form, tables['fw_primer'].form, tables['rv_primer'].form, tables['ack'].form, tables['tools'].form, tables['genotype_description'].form, tables['inferred_sequence'].form)
    return (tables, form)




