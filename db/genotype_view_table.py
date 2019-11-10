# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from imgt.imgt_ref import get_imgt_reference_genes, get_igpdb_ref, get_vdjbase_ref, get_reference_v_codon_usage, find_family, get_imgt_gapped_reference_genes, find_gapped_index, gap_sequence
from Bio import pairwise2, Seq
from Bio.Alphabet import generic_dna
from db.genotype_tables import *
import sys
import re

class SeqCol(StyledCol):
    def td_contents(self, item, attr_list):
        imgt_ref = get_imgt_reference_genes()
        imgt_ref_gapped = get_imgt_gapped_reference_genes()
        ref_codon_usage = get_reference_v_codon_usage()

        bt_view = '<button type="button" id="btn_view_seq" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
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
            igpdb_genes = get_igpdb_ref()
            for k,v in igpdb_genes.items():
                if item.nt_sequence.lower() in v or v in item.nt_sequence.lower():
                    bt_igpdb = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Sequence matches IGPDB gene %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % k
                    break

        bt_vdjbase = ''

        if item.genotype_description.submission.species == 'Human':
            vdjbase_genes = get_vdjbase_ref()
            for k,v in vdjbase_genes.items():
                if item.nt_sequence.lower() in v[0] or v[0] in item.nt_sequence.lower():
                    bt_vdjbase = '<button type="button" name="vdjbase_btn" id="vdjbase_btn" class="btn btn-xs text-info icon_back" data-toggle="tooltip" data-vdjbase_name="%s" title="Sequence matches VDJbase gene %s (found in %s subjects). Click to view in VDJbase."><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % \
                                 (k, k, v[1])
                    break

        bt_indels = ''
        bt_imgt = ''
        bt_codon_usage = ''
        bt_runs = ''
        bt_hotspots = ''
        bt_ref_found = ''

        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species]:
            if item.closest_reference not in imgt_ref[item.genotype_description.submission.species]:
                bt_ref_found = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Nearest reference not found in IMGT reference set"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>'
            else:
                for k,v in imgt_ref[item.genotype_description.submission.species].items():
                    if item.nt_sequence.lower() == v:
                        bt_imgt = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Sequence matches IMGT gene %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % k
                        break

                # QA Checks

                # Alignment issues

                ref_nt = imgt_ref[item.genotype_description.submission.species][item.closest_reference].upper()
                seq_nt = item.nt_sequence.upper()

                mismatch = 0
                aligned = True

                for (r,s) in zip(list(ref_nt), list(seq_nt)):
                    if r != s:
                        mismatch += 1

                if mismatch > 20:
                    aligned = False
                    bt_indels = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Sequence has indels/low match when compared to reference sequence"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>'

                if aligned:
                    # Check for unusual AAs at each position

                    if item.genotype_description.sequence_type == 'V' and item.genotype_description.locus+'V' in ref_codon_usage[item.genotype_description.submission.species]:
                        try:
                            q_codons = []
                            ref_aa_gapped = list(imgt_ref_gapped[item.genotype_description.submission.species][item.closest_reference].upper().translate(gap='.'))
                            seq_aa = Seq(item.nt_sequence.upper(), generic_dna).translate()

                            seq_aa_gapped = gap_sequence(seq_aa, ref_aa_gapped)
                            seq_aa_gapped = list(seq_aa_gapped)
                            family = find_family(item.closest_reference)

                            for i in range( min(len(ref_aa_gapped), len(seq_aa_gapped))):
                                if ref_aa_gapped[i] != seq_aa_gapped[i] and '*' not in (ref_aa_gapped[i], seq_aa_gapped[i]) and '.' not in (ref_aa_gapped[i], seq_aa_gapped[i]):
                                    if seq_aa_gapped[i] not in ref_codon_usage[item.genotype_description.submission.species][item.genotype_description.locus + 'V'][family][i+1]:
                                        q_codons.append("%s%d" % (seq_aa_gapped[i], i+1))

                            if len(q_codons) > 0:
                                bt_codon_usage = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Amino Acid(s) previously unreported in this family: %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % ", ".join(q_codons)

                        except:
                            bt_codon_usage = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Error translating sequence: %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % sys.exc_info()[0]

                    # Check for lengthened strings of the same base

                    ref_qpos = [m.start() for m in re.finditer('(.)\\1+\\1+\\1+', str(ref_nt))]
                    seq_qpos = [m.start() for m in re.finditer('(.)\\1+\\1+\\1+', str(seq_nt))]

                    q_runs = []

                    for p in seq_qpos:
                        if p not in ref_qpos:
                            q_runs.append("%d" % find_gapped_index(p, item.genotype_description.submission.species, item.closest_reference))

                    if len(q_runs) > 0:
                        bt_runs = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="Possible repeated read errors at IMGT position(s) %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % ", ".join(q_runs)

                    # Check for RGYW/WRCY hotspot change

                    ref_qpos = [m.start() for m in re.finditer('[AG][GC][CT][AT]', str(ref_nt))]
                    seq_qpos = [m.start() for m in re.finditer('[AG][GC][CT][AT]', str(seq_nt))]

                    q_hotspots= []

                    for p in seq_qpos:
                        if p in ref_qpos and list(ref_nt)[p+1] != list(seq_nt)[p+1]:
                            q_hotspots.append("%d" % find_gapped_index(p+1, item.genotype_description.submission.species, item.closest_reference))

                    ref_qpos = [m.start() for m in re.finditer('[AT][AG][GC][CT]', str(ref_nt))]
                    seq_qpos = [m.start() for m in re.finditer('[AT][AG][GC][CT]', str(seq_nt))]

                    for p in seq_qpos:
                        if p in ref_qpos and list(ref_nt)[p+2] != list(seq_nt)[p+2]:
                            q_hotspots.append("%d" % find_gapped_index(p+2, item.genotype_description.submission.species, item.closest_reference))

                    if len(q_hotspots) > 0:
                        bt_hotspots = '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="tooltip" title="G/C SNP in RGYW/WRCY hotspot at IMGT position(s) %s"><span class="glyphicon glyphicon-info-sign"></span>&nbsp;</button>' % ", ".join(q_hotspots)

        return bt_view + bt_check + bt_imgt + bt_igpdb + bt_vdjbase + bt_indels + bt_codon_usage + bt_runs + bt_hotspots + bt_ref_found

class GenTitleCol(StyledCol):
    def td_contents(selfself, item, attr_list):
        imgt_ref = get_imgt_reference_genes()
        text = item.sequence_id
        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species]:
            text = '<em>' + text + '</em>'
        if len(item.inferred_sequences) > 0:
            text = '<strong>' + text + '</strong>'
        return Markup(text)


def setup_gv_table(desc):
    table = make_Genotype_full_table(desc.genotypes, desc.locus, False, classes=['table-bordered'])
    table._cols['sequence_id'] = GenTitleCol('Allele name', tooltip='Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)')
    table.rotate_header = True
    table.add_column('nt_sequence', SeqCol('Sequence', tooltip="Click to view or download sequence"))
    table.table_id = 'genotype_table'

    inferred_seqs = []

    for inf in desc.inferred_sequences:
        inferred_seqs.append(inf.sequence_details.sequence_id)

    novel = []
    imgt_ref = get_imgt_reference_genes()
    for item in desc.genotypes:
        if item.sequence_id not in imgt_ref[item.genotype_description.submission.species] or item.sequence_id in inferred_seqs:
            novel.append(item)

    inferred_table = make_Genotype_novel_table(novel, False, classes = ['table-bordered'])
    inferred_table._cols['sequence_id'] = GenTitleCol('Allele name', tooltip='Identifier of the allele (either IMGT, or the name assigned by the submitter to an inferred gene)')
    inferred_table.add_column('nt_sequence', SeqCol('Sequence', tooltip="Click to view or download sequence"))
    inferred_table.rotate_header = True

    return (table, inferred_table)


def setup_gv_fasta(desc):
    f = ''
    for g in desc.genotypes:
        f += format_fasta_sequence(g.sequence_id, g.nt_sequence, 100)
    return f
