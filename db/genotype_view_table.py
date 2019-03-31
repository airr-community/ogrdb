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
from flask_table import create_table



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

        if item.genotype_description.submission.species == 'Human':
            igpdb_genes = igpdb_ref()
            for k,v in igpdb_genes.items():
                if item.nt_sequence.lower() == v:
                    bt_igpdb = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Sequence matches IGPDB gene %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % k
                    break

        bt_imgt = ''

        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species]:
            for k,v in imgt_ref[item.genotype_description.submission.species].items():
                if item.nt_sequence.lower() == v:
                    bt_imgt = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Sequence matches IMGT gene %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % k
                    break

        return bt_view + bt_check + bt_igpdb + bt_imgt

class GenTitleCol(StyledCol):
    def td_contents(selfself, item, attr_list):
        imgt_ref = imgt_reference_genes()
        text = item.sequence_id
        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species]:
            text = '<em>' + text + '</em>'
        if len(item.inferred_sequences) > 0:
            text = '<strong>' + text + '</strong>'
        return Markup(text)


# Definitions adapted from the auto-generated tables, to split the view in two

class Genotype_full_table(StyledTable):
    id = Col("id", show=False)
    sequence_id = StyledCol("Allele name", tooltip="Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)")
    sequences = StyledCol("Sequences", tooltip="Overall number of sequences assigned to this allele")
    unmutated_sequences = StyledCol("Unmutated Seqs", tooltip="The number of sequences exactly matching this unmutated sequence")
    assigned_unmutated_frequency = StyledCol("Unmutated % within allele", tooltip="The number of sequences exactly matching this allele divided by the number of sequences assigned to this allele, *100")
    unmutated_umis = StyledCol("Unmutated UMIs", tooltip="The number of molecules (identified by Unique Molecular Identifiers) exactly matching this unmutated sequence (if UMIs were used)")
    allelic_percentage = StyledCol("Allelic %", tooltip="The number of sequences exactly matching the sequence of this allele divided by the number of sequences exactly matching any allele of this specific gene, *100")
    unmutated_frequency = StyledCol("Total unmutated population (%)", tooltip="The number of sequences exactly matching the sequence of this allele divided by the number of sequences exactly matching any allele of any gene, *100")
    unique_ds = StyledCol("Unique Ds", tooltip="The number of D allele calls (i.e., unique allelic sequences) associated with this allele")
    unique_js = StyledCol("Unique Js", tooltip="The number of J allele calls (i.e., unique allelic sequences) associated with this allele")
    unique_cdr3s = StyledCol("Unique CDR3s", tooltip="The number of unique CDR3s associated with this allele")
    unique_ds_unmutated = StyledCol("Unique Ds with unmutated", tooltip="The number of D allele calls (i.e., unique allelic sequences) associated with unmutated sequences of this allele")
    unique_js_unmutated = StyledCol("Unique Js with unmutated", tooltip="The number of J allele calls (i.e., unique allelic sequences) associated with unmutated sequences of this allele")
    unique_cdr3s_unmutated = StyledCol("Unique CDR3s with unmutated", tooltip="The number of unique CDR3s associated with unmutated sequences of this allele")
    haplotyping_gene = StyledCol("Haplotyping Gene", tooltip="The gene (or genes) from which haplotyping was inferred (e.g. IGHJ6)")
    haplotyping_ratio = StyledCol("Haplotyping Ratio", tooltip="The ratio (expressed as two percentages) with which the two inferred haplotypes were found (e.g. 60:40)")


def make_Genotype_full_table(results, private = False, classes=()):
    t=create_table(base=Genotype_full_table)
    ret = t(results, classes=classes)
    return ret


class Genotype_novel_table(StyledTable):
    id = Col("id", show=False)
    sequence_id = StyledCol("Allele name", tooltip="Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)")
    sequences = StyledCol("Sequences", tooltip="Overall number of sequences assigned to this allele")
    closest_reference = StyledCol("Closest Reference", tooltip="For inferred alleles, the closest reference gene and allele")
    closest_host = StyledCol("Closest in Host", tooltip="For inferred alleles, the closest reference gene and allele that is in the subject's inferred genotype")
    nt_diff = StyledCol("NT Diffs", tooltip="For inferred alleles, the number of nucleotides that differ between this sequence and the closest reference gene and allele")
    nt_diff_host = StyledCol("NT Diffs (host)", tooltip="For inferred alleles, the number of nucleotides that differ between this sequence and the closest reference gene and allele that is in the subject's inferred genotype")
    nt_substitutions = StyledCol("NT Substs", tooltip="For inferred alleles, Comma-separated list of nucleotide substitutions (e.g. G112A) between this sequence and the closest reference gene and allele. Please use IMGT numbering for V-genes, and number from start of coding sequence for D- or J- genes.")
    aa_diff = StyledCol("AA Diffs", tooltip="For inferred alleles, the number of amino acids that differ between this sequence and the closest reference gene and allele")
    aa_substitutions = StyledCol("AA Substs", tooltip="For inferred alleles, the list of amino acid substitutions (e.g. A96N) between this sequence and the closest reference gene and allele. Please use IMGT numbering for V-genes, and number from start of coding sequence for D- or J- genes.")


def make_Genotype_novel_table(results, private = False, classes=()):
    t=create_table(base=Genotype_novel_table)
    ret = t(results, classes=classes)
    return ret



def setup_gv_table(desc):
    table = make_Genotype_full_table(desc.genotypes, False, classes = ['table-bordered'])
    table._cols['sequence_id'] = GenTitleCol('Allele name', tooltip='Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)')
    table.rotate_header = True
    table.add_column('nt_sequence', SeqCol('Sequence', tooltip="Click to view or download sequence"))
    table.table_id = 'genotype_table'

    novel = []
    imgt_ref = imgt_reference_genes()
    for item in desc.genotypes:
        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species]:
            novel.append(item)

    inferred_table = make_Genotype_novel_table(novel, False, classes = ['table-bordered'])
    inferred_table._cols['sequence_id'] = GenTitleCol('Allele name', tooltip='Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)')
    inferred_table.add_column('nt_sequence', SeqCol('Sequence', tooltip="Click to view or download sequence"))

    return (table, inferred_table)

def setup_gv_fasta(desc):
    f = ''
    for g in desc.genotypes:
        f += format_fasta_sequence(g.sequence_id, g.nt_sequence, 100)
    return f