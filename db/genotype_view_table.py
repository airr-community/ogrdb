# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#


from imgt.imgt_ref import imgt_reference_genes, igpdb_ref
from db.genotype_db import Genotype_table, make_Genotype_table
from db.styled_table import *
from Bio import pairwise2
from Bio.pairwise2 import format_alignment
from sequence_format import *


class SeqCol(StyledCol):
    def td_contents(self, item, attr_list):
        imgt_ref = imgt_reference_genes()

        bt_view =  '<button type="button" id="btn_view_seq" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
               % (format_nuc_sequence(item.nt_sequence, 50), item.sequence_id, format_fasta_sequence(item.sequence_id, item.nt_sequence, 50))

        if item.sequence_id in imgt_ref[item.genotype_description.submission.species]:
            if item.nt_sequence.lower() == imgt_ref[item.genotype_description.submission.species][item.sequence_id]:
                icon = 'glyphicon-ok'
                colour = 'text-info'
                aln_text = ' data-toggle="tooltip" title="Agrees with Reference"'
            else:
                icon = 'glyphicon-remove'
                colour = 'text-danger'
                alignments = pairwise2.align.globalms(item.nt_sequence.lower(), imgt_ref[item.genotype_description.submission.species][item.sequence_id], 2, -1, -2, -1, one_alignment_only=True)
                alignment = format_aln(format_alignment(*alignments[0]), item.sequence_id, 'Reference', 50)
                fasta_seqs = format_fasta_sequence(item.sequence_id, item.nt_sequence.lower(), 50) + format_fasta_sequence('Reference', imgt_ref[item.genotype_description.submission.species][item.sequence_id], 50)
                aln_text =  Markup(' id="btn_view_check" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="modal" title="Differs from Reference (click to view)"' %
                    (alignment, item.sequence_id, fasta_seqs))


            bt_check = '<button type="button" class="btn btn-xs %s icon_back" %s><span class="glyphicon %s"></span>&nbsp;</button>' \
                        % (colour, aln_text, icon)
        else:
            bt_check = ''

        bt_igpdb = ''

        if item.genotype_description.submission.species == 'Human' and item.sequence_id not in imgt_ref['Human']:
            igpdb_genes = igpdb_ref()
            for k,v in igpdb_genes.items():
                if item.nt_sequence.lower() == v:
                    bt_igpdb = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Sequence matches IGPDB gene %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % k
                    break

        return bt_view + bt_check + bt_igpdb

class GenTitleCol(StyledCol):
    def td_contents(selfself, item, attr_list):
        imgt_ref = imgt_reference_genes()
        text = item.sequence_id
        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species]:
            text = '<em>' + text + '</em>'
        if len(item.inferred_sequences) > 0:
            text = '<strong>' + text + '</strong>'
        return Markup(text)


def setup_gv_table(desc):
    table = make_Genotype_table(desc.genotypes, False, classes = ['table-bordered'])
    table._cols['sequence_id'] = GenTitleCol('Allele name', tooltip='Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)')
    table.rotate_header = True
    table.add_column('nt_sequence', SeqCol('Sequence', tooltip="Click to view or download sequence"))
    return table

def setup_gv_fasta(desc):
    f = ''
    for g in desc.genotypes:
        f += format_fasta_sequence(g.sequence_id, g.nt_sequence, 100)
    return f