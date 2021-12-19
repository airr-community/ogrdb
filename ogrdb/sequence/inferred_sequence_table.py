# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#
from operator import attrgetter

from ogrdb.submission.submission_edit_form import EditableAckTable, EditableAttachedFileTable
from db.repertoire_db import make_Acknowledgements_table
from db.attached_file_db import *
from db.journal_entry_db import *
from forms.repertoire_form import AcknowledgementsForm
from forms.attached_file_form import *
from textile_filter import *
from flask import url_for
from db.gene_description_db import *
from sequence_format import *
from db.vdjbase import get_vdjbase_ref

class MessageHeaderCol(StyledCol):
    def td_contents(self, item, attr_list):
        return "<strong>%s</strong><br><small>%s</small>" % (item.author, item.date)

class MessageBodyCol(StyledCol):
    def td_contents(self, item, attr_list):
        return Markup(safe_textile(item.body)) if item.parent is not None else "<strong>%s</strong><br>%s" % (item.title, Markup(safe_textile(item.body)))

class InferredSequenceTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = '''
        <button type="button" class="del_inf_button btn btn-xs text-danger icon_back" 
        data-id="%s" data-inf="%s" id="del_inf_%s_%s" data-toggle="tooltip" 
        title="Delete">
        <span class="glyphicon glyphicon-trash"></span>&nbsp;
        </button>
        ''' % (item['id'], item['sequence_id'], item['id'], item['sequence_id'])
        return(contents)

class InferredSequenceTableMatchCol(StyledCol):
    def td_contents(self, item, attr_list):
        if item['gene_sequence'] == item['nt_sequence']:
            icon = 'glyphicon-ok'
            colour = 'text-info'
        else:
            icon = 'glyphicon-remove'
            colour = 'text-danger'

        alignment = report_dupe(item['gene_sequence'], 'Sequence', item['nt_sequence'], item['sequence_name'])
        content = Markup('''
        <button id="aln_view" name="aln_view" type="button" 
        class="btn btn-xs %s icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" 
        data-toggle="tooltip" 
        title="View">
        <span class="glyphicon %s"></span>&nbsp;
        </button>
        ''' % (colour, alignment, item['sequence_name'], format_fasta_sequence(item['allele_name'], item['gene_sequence'], 50) + format_fasta_sequence(item['sequence_name'], item['nt_sequence'], 50), icon))
        return(content)

class SubLinkCol(StyledCol):
    def td_format(self, content):
        return Markup('<a href="%s">%s</span>&nbsp;</a>' % (url_for('submission', id=content), content))


class InferredSequenceTable(StyledTable):
    submission_id = SubLinkCol("Submission ID", tooltip='Submission from which this inference was taken')
    accession_no = StyledCol("Accession No", tooltip='Accession Number in Genbank or other repository')
    subject_id = StyledCol("Subject ID", tooltip="ID of the subject from which this sequence was inferred")
    genotype_name = StyledCol("Genotype Name", tooltip="Name of genotype from which sequence was drawn")
    sequence_link = StyledCol("Sequence Name", tooltip="Name of inferred sequence as referred to in the submission")

def make_InferredSequence_table(results, private = False, classes=()):
    t = create_table(base=InferredSequenceTable)
    ret = t(results, classes=classes)
    return ret

def setup_inferred_sequence_table(seqs, gene_desc, action=True):
    results = []
    for seq in seqs:
        ncbi = seq.submission.repertoire[0].repository_name == 'NCBI SRA'
        ena = seq.submission.repertoire[0].repository_name == 'ENA'
        acc = Markup('<a href="https://www.ncbi.nlm.nih.gov/nuccore/%s">%s</a>' % (seq.seq_accession_no, seq.seq_accession_no)) if ncbi \
            else Markup('<a href="https://www.ebi.ac.uk/ena/data/view/%s">%s</a>' % (seq.seq_accession_no, seq.seq_accession_no)) if ena \
            else seq.seq_accession_no
        name = Markup('<a href="%s">%s</a>' % (url_for('inferred_sequence', id=seq.id), seq.sequence_details.sequence_id))
        gen = Markup('<a href="%s">%s</a>' % (url_for('genotype', id=seq.genotype_description.id), seq.genotype_description.genotype_name))
        results.append({'submission_id': seq.submission.submission_id,
                        'accession_no': acc,
                        'sequence_link': name,
                        'sequence_name': seq.sequence_details.sequence_id,
                        'id': gene_desc.id,
                        'gene_sequence': gene_desc.sequence.replace('.', '').lower() if gene_desc.sequence else '',
                        'sequence_id': seq.id,
                        'nt_sequence': seq.sequence_details.nt_sequence.lower() if seq.sequence_details.nt_sequence else '',
                        'subject_id': seq.genotype_description.genotype_subject_id,
                        'genotype_name': gen,
                        'allele_name': gene_desc.description_id})
    table = make_InferredSequence_table(results)
    table.add_column('match', InferredSequenceTableMatchCol('Sequence Match', tooltip="Ticked if the sequence exactly matches this inference. Click for alignment."))

    if action:
        table.add_column('action', InferredSequenceTableActionCol(''))
        table._cols.move_to_end('action', last=False)
    return table


class SupportingObservationTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = '''
        <button type="button" 
        class="del_obs_button btn btn-xs text-danger icon_back" 
        data-id="%s" data-gid="%s" id="del_obs_%s_%s" data-toggle="tooltip" 
        title="Delete">
        <span class="glyphicon glyphicon-trash"></span>&nbsp;
        </button>
        ''' % (item['gene_description_id'], item['genotype_id'], item['gene_description_id'], item['genotype_id'])
        return(contents)


class SupportingObservationTable(StyledTable):
    submission_id = SubLinkCol("Submission ID", tooltip='Submission from which this inference was taken')
    subject_id = StyledCol("Subject ID", tooltip="ID of the subject from which this sequence was inferred")
    genotype_name = StyledCol("Genotype Name", tooltip="Name of genotype from which sequence was drawn")
    sequence_name = StyledCol("Sequence Name", tooltip="Name of inferred sequence as referred to in the submission")

def make_SupportingObservation_table(results, private = False, classes=()):
    t = create_table(base=SupportingObservationTable)
    ret = t(results, classes=classes)
    return ret

def setup_supporting_observation_table(seq, action=True):
    results = []
    for genotype in seq.supporting_observations:
        gen = Markup('<a href="%s">%s</a>' % (url_for('genotype', id=genotype.genotype_description.id), genotype.genotype_description.genotype_name))
        results.append({'submission_id': genotype.genotype_description.submission.submission_id, 'subject_id': genotype.genotype_description.genotype_subject_id, 'genotype_name': gen, 'sequence_name': genotype.sequence_id,
                        'allele_name': genotype.sequence_id, 'gene_sequence': seq.sequence_details.sequence, 'nt_sequence': genotype.nt_sequence, 'genotype_id': genotype.id, 'gene_description_id': seq.id})

    table = make_SupportingObservation_table(results)
    table.add_column('match', InferredSequenceTableMatchCol('Sequence Match', tooltip="Ticked if the sequence exactly matches this inference. Click for alignment."))

    if action:
        table.add_column('action', SupportingObservationTableActionCol(''))
        table._cols.move_to_end('action', last=False)

    return table

class VDJbaseTable(StyledTable):
    vdjbase_name = StyledCol("VDJbase Allele Name", tooltip='Name of matching allele in VDJbase')
    subjects = StyledCol("Subjects", tooltip="Number of subjects in which the allele was observed")

def make_VDJbase_table(results, private = False, classes=()):
    t = create_table(base=VDJbaseTable)
    ret = t(results, classes=classes)
    return ret

def setup_vdjbase_matches_table(seq):
    results = []

    vdjbase_ref = get_vdjbase_ref()
    vdjbase_species = seq.species.replace('Human_TCR', 'Human')
    if seq.coding_seq_imgt is not None and len(seq.coding_seq_imgt) > 0 \
            and vdjbase_species in vdjbase_ref and seq.locus in vdjbase_ref[vdjbase_species]:
        vdjbase_genes = vdjbase_ref[vdjbase_species][seq.locus]
        gene_seq = seq.coding_seq_imgt.lower().replace('.', '')
        for vdjbase_name, (vdjbase_seq, vdjbase_count) in vdjbase_genes.items():
            if (gene_seq in vdjbase_seq or vdjbase_seq in gene_seq) and vdjbase_count != '0':
                results.append(
                    {'vdjbase_name': Markup('<a href="%sgenerep/%s/%s/%s"> %s </a>' % (app.config['VDJBASE_URL'], vdjbase_species, seq.locus, vdjbase_name, vdjbase_name)),
                     'allele_name': vdjbase_name,
                     'subjects': vdjbase_count,
                     'nt_sequence': vdjbase_seq,
                     'sequence_name': seq.sequence_name,
                     'gene_sequence': gene_seq})

    table = make_VDJbase_table(results)
    table.add_column('match', InferredSequenceTableMatchCol('Sequence Match', tooltip="Ticked if the sequence exactly matches this inference. Click for alignment."))

    return table

class MatchingSubmissionsTableMatchCol(StyledCol):
    def td_contents(self, item, attr_list):
        if item['gene_sequence'] == item['nt_sequence']:
            icon = 'glyphicon-ok'
            colour = 'text-info'
        else:
            icon = 'glyphicon-remove'
            colour = 'text-danger'

        # identical chars 2 points, -1 for non-identical, -2 for opening a gap, -1 for extending it
        alignment = report_dupe(item['gene_sequence'], 'Sequence', item['nt_sequence'], item['sequence_name'])
        content = Markup('''
        <button id="aln_view" name="aln_view" type="button" 
        class="btn btn-xs %s icon_back" 
        data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" 
        data-toggle="tooltip" title="View">
        <span class="glyphicon %s"></span>&nbsp;
        </button>
        ''' % (colour, alignment, item['sequence_name'], format_fasta_sequence(item['allele_name'], item['gene_sequence'], 50) + format_fasta_sequence(item['sequence_name'], item['nt_sequence'], 50), icon))
        return(content)


class MatchingSubmissionsTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = ''
        if item['add_action']:
            if item['inferred_id'] is None:
                contents += '''
                <button type="button" 
                class="add_obs_button btn btn-xs text-default icon_back" 
                data-id="%s" data-gid="%s" id="add_obs_%s_%s" 
                data-toggle="tooltip" title="Add">
                <span class="glyphicon glyphicon-plus"></span>&nbsp;
                </button>
                ''' % (item['gene_description_id'], item['genotype_id'], item['gene_description_id'], item['genotype_id'])
            else:
                contents += '''
                <button type="button" 
                class="add_inf_button btn btn-xs text-default icon_back" 
                data-id="%s" data-inf="%s" id="add_inf_%s_%s" 
                data-toggle="tooltip" title="Add">
                <span class="glyphicon glyphicon-plus"></span>&nbsp;
                </button>
                ''' % (item['gene_description_id'], item['inferred_id'], item['gene_description_id'], item['inferred_id'])

        notes_icon = 'glyphicon-list-alt' if item['notes_present'] else 'glyphicon-unchecked'
        notes_tooltip = 'View/modify note' if item['notes_present'] else 'Add note'
        contents += '''
        <button type="button" 
        class="dupe_notes_button btn btn-xs text-default icon_back" 
        data-genotype_id="%s" data-sequence_id="%s" id="add_inf_%s_%s" 
        title="%s">
        <span class="glyphicon %s"></span>&nbsp;
        </button>
        ''' % (item['genotype_id'], item['gene_description_id'], item['genotype_id'], item['inferred_id'], notes_tooltip, notes_icon)

        return contents

class MatchingSubmissionsTableInfCol(StyledCol):
    def td_contents(selfself, item, attr_list):
        if item['inferred_id'] is not None:
            return(Markup('<a href="%s">%s</a>' % (url_for('inferred_sequence', id = item['inferred_id']), item['sequence_name'])))
        else:
            return item['sequence_name']


class MatchingSubmissionsTable(StyledTable):
    submission_id = SubLinkCol("Submission ID", tooltip='Submission containing the matching inference')
    accession_no = StyledCol("Accession No", tooltip='Accession Number in Genbank or other repository')
    subject_id = StyledCol("Subject ID", tooltip="ID of the subject from which this sequence was inferred")
    genotype_name = StyledCol("Genotype Name", tooltip="Name of genotype from which sequence was drawn")
    sequence_name = MatchingSubmissionsTableInfCol("Sequence Name", tooltip="Name of inferred sequence as referred to in the submission")
    match = MatchingSubmissionsTableMatchCol("Match", tooltip="Details of the match")



def make_MatchingSubmissions_table(results, classes=()):
    t=create_table(base=MatchingSubmissionsTable)
    ret = t(results, classes=classes)
    return ret

def setup_matching_submissions_table(seq, add_action=True):
    results = []
    our_descs = []

    for inf in seq.inferred_sequences:
        our_descs.append(inf.sequence_details)

    for gen in seq.supporting_observations:
        our_descs.append(gen)

    noted_dupes = []

    for dn in seq.dupe_notes:
        noted_dupes.append(dn.genotype_id)

    for dup in seq.duplicate_sequences:
        if dup not in our_descs:
            if len(dup.inferred_sequences) > 0:
                inf = dup.inferred_sequences[0]
                inferred_id = inf.id
                ncbi = dup.genotype_description.submission.repertoire[0].repository_name == 'NCBI SRA'
                acc = Markup('<a href="https://www.ncbi.nlm.nih.gov/nuccore/%s">%s</a>' % (inf.seq_accession_no, inf.seq_accession_no)) if ncbi else inf.seq_accession_no
            else:
                inferred_id = None
                acc = ''

            gen = Markup('<a href="%s">%s</a>' % (url_for('genotype', id=dup.genotype_description.id), dup.genotype_description.genotype_name))
            results.append({'submission_id': dup.genotype_description.submission.submission_id,
                            'accession_no': acc,
                            'allele_name': seq.description_id,
                            'subject_id': dup.genotype_description.genotype_subject_id,
                            'genotype_name': gen,
                            'gene_sequence': seq.sequence,
                            'nt_sequence': dup.nt_sequence,
                            'inferred_id': inferred_id,
                            'sequence_name': dup.sequence_id,
                            'gene_description_id': seq.id, 'genotype_id': dup.id,
                            'add_action': add_action,
                            'notes_present': dup.id in noted_dupes})

    if len(results) == 0:
        return None

    table = make_MatchingSubmissions_table(results)

    table.add_column('action', MatchingSubmissionsTableActionCol(''))
    table._cols.move_to_end('action', last=False)

    return table

class GenomicSupportTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = '''
        <button type="button" 
        class="del_genomic_button btn btn-xs text-danger icon_back" 
        data-id="%s" data-gen="%s" id="del_gen_%s_%s" data-toggle="tooltip" 
        title="Delete">
        <span class="glyphicon glyphicon-trash"></span>&nbsp;
        </button>
        ''' % (item.sequence_id, item.id, item.sequence_id, item.id)
        contents += ('''
        <a href="%s" 
        class="btn btn-xs text-warning icon_back">
        <span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Edit"></span>&nbsp;
        </a>
        ''' % (url_for('seq_edit_genomic', seq_id=item.sequence_id, support_id=item.id)))
        return(contents)

def setup_genomic_support_table(seq, action=True):
        table = make_GenomicSupport_table(seq.genomic_accessions)
        del(table._cols['accession'])
        table.add_column('acc', StyledCol("Accession", tooltip="Genbank or ENA accession number, e.g MK321684"))
        table._cols.move_to_end('acc', last=False)

        if action:
            table.add_column('action', GenomicSupportTableActionCol(""))
            table._cols.move_to_end('action', last=False)

        for item in table.items:
            item.acc = Markup('<a href="%s">%s</a>' % (url_for('genomic_support', id=item.id), item.accession))

        return table


class GeneDescription_difference_view(Table):
    item = ViewCol("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")
    value2 = Col("")


def list_sequence_changes(gene_description):
    if gene_description.status == 'draft':
        prev = db.session.query(GeneDescription).filter(GeneDescription.description_id == gene_description.description_id, GeneDescription.status == 'published').one_or_none()
        if prev is None:
            prevs = db.session.query(GeneDescription).filter(GeneDescription.description_id == gene_description.description_id, GeneDescription.status == 'superceded').all()

            if len(prevs) > 0:
                prev = prevs.sorted(key=attrgetter('release_version'))[0]
    else:
        prev = None
        prevs = db.session.query(GeneDescription)\
            .filter(GeneDescription.description_id == gene_description.description_id, GeneDescription.status.in_(['published', 'superceded']))\
            .filter(GeneDescription.release_version < gene_description.release_version)\
            .all()

        if len(prevs) > 0:
            prev = sorted(prevs, key=attrgetter('release_version'), reverse=True)[0]

    if prev is None:
        return None

    prev_view = make_GeneDescription_view(prev)
    this_view = make_GeneDescription_view(gene_description)
    diff_view = GeneDescription_difference_view([])

    for i in range(len(prev_view.items)):
        if prev_view.items[i]['value'] != this_view.items[i]['value'] \
                and prev_view.items[i]['item'] not in ('Version', 'Release Notes', 'Release Date'):
            item = prev_view.items[i]
            item['value2'] = this_view.items[i]['value']
            diff_view.items.append(item)
        elif prev_view.items[i]['item'] == 'Version':
            diff_view.value.name = 'v' + str(prev_view.items[i]['value'])
            diff_view.value2.name = ('v' + str(this_view.items[i]['value']) if gene_description.status != 'draft' else 'draft')

    if prev.notes != gene_description.notes:
        item = {'item': 'Notes', 'value': '', 'value2': 'changed', 'field': 'notea'}
        diff_view.items.append(item)

    return diff_view if len(diff_view.items) > 0 else None



def setup_sequence_edit_tables(db, seq):
    tables = {}
    tables['inferred_sequence'] = setup_inferred_sequence_table(seq.inferred_sequences, seq)
    tables['supporting_observations'] = setup_supporting_observation_table(seq)
    tables['genomic_support'] = setup_genomic_support_table(seq, action=True)
    tables['ack'] = EditableAckTable(make_Acknowledgements_table(seq.acknowledgements), 'ack', AcknowledgementsForm, seq.acknowledgements, legend='Add Acknowledgement')
    tables['matches'] = setup_matching_submissions_table(seq)
    tables['attachments'] = EditableAttachedFileTable(make_AttachedFile_table(seq.attached_files), 'attached_files', AttachedFileForm, seq.attached_files, legend='Attachments', delete_route='delete_sequence_attachment', delete_message='Are you sure you wish to delete the attachment?', download_route='download_sequence_attachment')
    tables['diffs'] = list_sequence_changes(seq)

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

