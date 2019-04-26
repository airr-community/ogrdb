# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from forms.submission_edit_form import EditableAckTable, EditableAttachedFileTable
from db.repertoire_db import make_Acknowledgements_table
from db.attached_file_db import *
from forms.repertoire_form import AcknowledgementsForm
from forms.attached_file_form import *
from textile_filter import *
from flask import url_for
from db.styled_table import *
from db.gene_description_db import *
from sequence_format import *
from flask import Markup
from Bio import pairwise2
from Bio.pairwise2 import format_alignment
from sequence_format import *


class InferredSequenceTableActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        contents = '<button type="button" class="delbutton btn btn-xs text-danger icon_back" data-id="%s" data-inf="%s" id="%s_%s" data-toggle="tooltip" title="Delete"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>' % (item['id'], item['sequence_id'], item['id'], item['sequence_id'])
        return(contents)

class InferredSequenceTableMatchCol(StyledCol):
    def td_contents(self, item, attr_list):
        if item['gene_sequence'] == item['nt_sequence']:
            icon = 'glyphicon-ok'
            colour = 'text-info'
        else:
            icon = 'glyphicon-remove'
            colour = 'text-danger'

        # identical chars 2 points, -1 for non-identical, -2 for opening a gap, -1 for extending it
        alignments = pairwise2.align.globalms(item['gene_sequence'], item['nt_sequence'], 2, -1, -2, -1, one_alignment_only=True)
        alignment = format_aln(format_alignment(*alignments[0]), 'Sequence', item['sequence_name'], 50)
        content =  Markup('<button id="aln_view" name="aln_view" type="button" class="btn btn-xs %s icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon %s"></span>&nbsp;</button>' \
            % (colour, alignment, item['sequence_name'], format_fasta_sequence(item['allele_name'], item['gene_sequence'], 50) + format_fasta_sequence(item['sequence_name'], item['nt_sequence'], 50), icon))
        return(content)

class SubLinkCol(StyledCol):
    def td_format(self, content):
        return Markup('<a href="%s">%s</span>&nbsp;</a>'  % (url_for('submission', id=content), content))

class InferredSequenceTable(StyledTable):
    submission_id = SubLinkCol("Submission ID", tooltip='Submission from which this inference was taken')
    accession_no = StyledCol("Accession No", tooltip='Accession Number in Genbank or other repository')
    subject_id = StyledCol("Subject ID", tooltip="ID of the subject from which this sequence was inferred")
    genotype_name = StyledCol("Genotype Name", tooltip="Name of genotype from which sequence was drawn")
    sequence_link = StyledCol("Sequence Name", tooltip="Name of inferred sequence as referred to in the submission")

def make_InferredSequence_table(results, private = False, classes=()):
    t=create_table(base=InferredSequenceTable)
    ret = t(results, classes=classes)
    return ret

class MessageHeaderCol(StyledCol):
    def td_contents(self, item, attr_list):
        return "<strong>%s</strong><br><small>%s</small>" % (item.author, item.date)

class MessageBodyCol(StyledCol):
    def td_contents(self, item, attr_list):
        return Markup(safe_textile(item.body)) if item.parent is not None else "<strong>%s</strong><br>%s" % (item.title, Markup(safe_textile(item.body)))

def setup_inferred_sequence_table(seqs, gene_desc, action=True):
    results = []
    for seq in seqs:
        ncbi =  seq.submission.repertoire[0].repository_name == 'NCBI SRA'
        acc = Markup('<a href="https://www.ncbi.nlm.nih.gov/nuccore/%s">%s</a>' % (seq.seq_accession_no, seq.seq_accession_no)) if ncbi else seq.seq_accession_no
        name = Markup('<a href="%s">%s</a>' % (url_for('inferred_sequence', id=seq.id), seq.sequence_details.sequence_id))
        gen = Markup('<a href="%s">%s</a>' % (url_for('genotype', id=seq.genotype_description.id), seq.genotype_description.genotype_name))
        results.append({'submission_id': seq.submission.submission_id, 'accession_no': acc, 'sequence_link': name, 'sequence_name': seq.sequence_details.sequence_id, 'id': gene_desc.id, 'gene_sequence': gene_desc.sequence.replace('.', '').lower() if gene_desc.sequence else '',
                        'sequence_id': seq.id, 'nt_sequence': seq.sequence_details.nt_sequence.lower() if seq.sequence_details.nt_sequence else '', 'subject_id': seq.genotype_description.genotype_subject_id,
                        'genotype_name': gen, 'allele_name': gene_desc.description_id})
    table = make_InferredSequence_table(results)
    table.add_column('match', InferredSequenceTableMatchCol('Sequence Match', tooltip="Ticked if the sequence exactly matches this inference. Click for alignment."))

    if action:
        table.add_column('action', InferredSequenceTableActionCol(''))
        table._cols.move_to_end('action', last=False)
    return table

class MatchingSubmissionsTable(StyledTable):
    submission_id = SubLinkCol("Submission ID", tooltip='Submission containing the matching inference')
    subject_id = StyledCol("Subject ID", tooltip="ID of the subject from which this sequence was inferred")
    genotype_name = StyledCol("Genotype Name", tooltip="Name of genotype from which sequence was drawn")
    sequence_name = StyledCol("Sequence Name", tooltip="Name of inferred sequence as referred to in the submission")
    match = StyledCol("Match", tooltip="Details of the match")

def make_MatchingSubmissions_table(results, classes=()):
    t=create_table(base=MatchingSubmissionsTable)
    ret = t(results, classes=classes)
    return ret

def setup_matching_submissions_table(seq):
    results = []
    for dup in seq.duplicate_sequences:
        if dup not in seq.inferred_sequences:
            match = report_dupe(seq.sequence, 'This', dup.sequence_details.nt_sequence, dup.submission.submission_id)
            if '\n' in match:
                match = Markup('<code>' + match.replace('\n', '<br>') + '</code>')
            results.append({'submission_id': dup.submission.submission_id, 'sequence_name': dup.sequence_details.sequence_id, 'match': Markup(match),
                            'subject_id': dup.genotype_description.genotype_subject_id, 'genotype_name': dup.genotype_description.genotype_name})

    if len(results) == 0:
        return None

    table = make_MatchingSubmissions_table(results)
    return table

def setup_sequence_edit_tables(db, seq):
    tables = {}
    tables['inferred_sequence'] = setup_inferred_sequence_table(seq.inferred_sequences, seq)
    tables['ack'] = EditableAckTable(make_Acknowledgements_table(seq.acknowledgements), 'ack', AcknowledgementsForm, seq.acknowledgements, legend='Add Acknowledgement')
    tables['matches'] = setup_matching_submissions_table(seq)
    tables['attachments'] = EditableAttachedFileTable(make_AttachedFile_table(seq.attached_files), 'attached_files', AttachedFileForm, seq.attached_files, legend='Attachments', delete_route='delete_sequence_attachment', delete_message='Are you sure you wish to delete the attachment?', download_route='download_sequence_attachment')

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

