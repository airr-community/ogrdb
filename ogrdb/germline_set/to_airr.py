# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import json
import re

# Create AIRR representation of items defined in the schema


def germline_set_to_airr(germline_set, extend, taxonomy, fake_allele=False):
    gds = []
    if extend:
        sequences = {}
        for gd in germline_set.gene_descriptions:
            if gd.coding_seq_imgt not in sequences:
                sequences[gd.coding_seq_imgt] = []
            sequences[gd.coding_seq_imgt].append(gd)

        for gd_group in sequences.values():
            rep = None
            lowest_subgroup = 9999
            for gd in gd_group:
                if gd.paralog_rep:
                    rep = gd
                    break
                try:
                    if int(re.sub(r"[^0-9]", "", gd.gene_subgroup)) < lowest_subgroup:
                        lowest_subgroup = int(re.sub(r"[^0-9]", "", gd.gene_subgroup))
                        rep = gd
                except:
                    pass

            if not rep:
                rep = sorted([gd for gd in gd_group], key=lambda x: x.sequence_name)[0]

            gds.append(rep)

    else:
        gds.extend(germline_set.gene_descriptions)

    ad = []
    for desc in gds:
        ad.append(vars(AIRRAlleleDescription(desc, extend, fake_allele, taxonomy=taxonomy)))

    gs = {'GermlineSet': [vars(AIRRGermlineSet(germline_set, ad, taxonomy=taxonomy))]}

    if extend:
        gs['GermlineSet'][0]['germline_set_name'] += '_extended'

    return gs


# Enforce schema constraints on capitalisation, and use None explicitly rather than empty string
def enum_choice(val, choice_list):
    if not val:
        return None
    
    for choice in choice_list:
        if val.upper().replace('-', '_') == choice.upper().replace('-', '_'):
            return choice
        
    return None


# Force 'falsey' values to None
# This is safe to use on co-ordinates because they are 1 based.
def fnone(val):
    if not val:
        return None
    else:
        return val

class AIRRAlleleDescription:
    def __init__(self, gd, extend, fake_allele, taxonomy=0):
        self.allele_description_id = 'OGRDB:' + gd.description_id
        
        if not gd.species_subgroup:
            self.allele_description_ref = f"OGRDB:{gd.species}:{gd.sequence_name}.{gd.release_version}{'_ext' if extend else ''}"
        else:
            self.allele_description_ref = f"OGRDB:{gd.species}/{gd.species_subgroup}_{gd.locus}:{gd.sequence_name}.{gd.release_version}{'_ext' if extend else ''}"
        
        self.maintainer = fnone(gd.maintainer)
        self.acknowledgements = []
        for ack in gd.acknowledgements:
            self.acknowledgements.append({
                'acknowledgement_id': str(ack.id),
                'name': ack.ack_name,
                'institution_name': ack.ack_institution_name,
                'ORCID_id': ack.ack_ORCID_id
            })
        self.acknowledgements = fnone(self.acknowledgements)
        self.lab_address = fnone(gd.lab_address)
        self.release_version = gd.release_version
        self.release_date = gd.release_date.strftime('%d-%b-%Y') if gd.release_date else "01-01-1970"
        self.release_description = fnone(gd.release_description)
        self.label = gd.sequence_name

        if fake_allele:
            if '*' not in self.label:
                self.label += '*00'
            if self.label[4] == '-':
                self.label = self.label.replace('-', '0-')

        self.sequence = gd.sequence
        self.coding_sequence = gd.coding_seq_imgt.replace('.', '')
        if extend and gd.ext_3prime:
            self.coding_sequence += gd.ext_3prime
        self.ext_3prime = fnone(gd.ext_3prime)
        self.aliases = []
        if gd.alt_names and len(gd.alt_names) > 0:
            self.aliases = gd.alt_names.split(',')
        self.aliases = fnone(self.aliases)
        self.locus = enum_choice(gd.locus, ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG'])
        self.chromosome = fnone(gd.chromosome)
        self.sequence_type = enum_choice(gd.sequence_type, ['V', 'D', 'J', 'C'])
        self.functional = 'F' in gd.functionality
        self.inference_type = enum_choice(gd.inference_type, ['Genomic and rearranged', 'Genomic only', 'Rearranged only'])
        self.species = {'id': f'NCBITAXON:{taxonomy}', 'label': gd.species}
        self.species_subgroup = fnone(gd.species_subgroup)
        self.species_subgroup_type = enum_choice(gd.species_subgroup_type, ['breed', 'strain', 'inbred', 'outbred', 'locational'])
        self.status = enum_choice(gd.status, ['active', 'draft', 'retired', 'withdrawn'])
        self.gene_designation = fnone(gd.gene_subgroup)
        self.subgroup_designation = fnone(gd.subgroup_designation)
        self.allele_designation = fnone(gd.allele_designation)
        self.allele_similarity_cluster_designation = None
        self.allele_similarity_cluster_member_id = None
        self.gene_start = gd.gene_start
        self.gene_end = gd.gene_end

        if self.sequence_type == 'V':
            self.utr_5_prime_start = fnone(gd.utr_5_prime_start)
            self.utr_5_prime_end = fnone(gd.utr_5_prime_end)
            self.leader_1_start = fnone(gd.leader_1_start)
            self.leader_1_end = fnone(gd.leader_1_end)
            self.leader_2_start = fnone(gd.leader_2_start)
            self.leader_2_end = fnone(gd.leader_2_end)
            self.v_rs_start = fnone(gd.v_rs_start)
            self.v_rs_end = fnone(gd.v_rs_end)

            cs = gd.coding_seq_imgt

            while cs[-1] == '.':    # remove trailing gaps
                cs = cs[:-1]

            if extend and gd.ext_3prime:
                cs += gd.ext_3prime

            self.v_gene_delineations = [{
                'sequence_delineation_id': "1",
                'delineation_scheme': 'IMGT',
                'unaligned_sequence': cs.replace('.', ''),
                'aligned_sequence': cs,
                'fwr1_start': 1,
                'fwr1_end': gd.cdr1_start - 1 - gd.gene_start + 1 if gd.cdr1_start else None,
                'cdr1_start': gd.cdr1_start - gd.gene_start + 1 if gd.cdr1_start else None,
                'cdr1_end': gd.cdr1_end - gd.gene_start + 1 if gd.cdr1_end else None,
                'fwr2_start': gd.cdr1_end + 1 - gd.gene_start + 1 if gd.cdr1_end else None,
                'fwr2_end': gd.cdr2_start - 1 - gd.gene_start + 1 if gd.cdr2_start else None,
                'cdr2_start': gd.cdr2_start - gd.gene_start + 1 if gd.cdr2_start else None,
                'cdr2_end': gd.cdr2_end - gd.gene_start + 1 if gd.cdr2_end else None,
                'fwr3_start': gd.cdr2_end + 1 - gd.gene_start + 1 if gd.cdr2_end else None,
                'fwr3_end': gd.cdr3_start - 1 - gd.gene_start + 1 if gd.cdr3_start else None,
                'cdr3_start': gd.cdr3_start - gd.gene_start + 1 if gd.cdr3_start else None,
                'alignment_labels': [],
            }]
            for i in range(1, 105):
                self.v_gene_delineations[0]['alignment_labels'].append('%d' % i)

        if self.sequence_type == 'D':
            self.d_rs_3_prime_start = fnone(gd.d_rs_3_prime_start)
            self.d_rs_3_prime_end = fnone(gd.d_rs_3_prime_end)
            self.d_rs_5_prime_start = fnone(gd.d_rs_5_prime_start)
            self.d_rs_5_prime_end = fnone(gd.d_rs_5_prime_end)

        if self.sequence_type == 'J':
            self.j_codon_frame = None if not gd.j_codon_frame else (int(gd.j_codon_frame) if gd.j_codon_frame in [1, 2, 3, '1', '2', '3'] else None)
            self.j_cdr3_end = fnone(gd.j_cdr3_end)
            self.j_rs_start = fnone(gd.j_rs_start)
            self.j_rs_end = fnone(gd.j_rs_end)

        if self.sequence_type == 'C':
            self.secretory_coding_sequence = fnone(gd.secretory_coding_sequence)
            self.c_exon_1_start = fnone(gd.c_exon_1_start)
            self.c_exon_1_end = fnone(gd.c_exon_1_end)
            self.c_exon_2_start = fnone(gd.c_exon_2_start)
            self.c_exon_2_end = fnone(gd.c_exon_2_end)
            self.c_exon_3_start = fnone(gd.c_exon_3_start)
            self.c_exon_3_end = fnone(gd.c_exon_3_end)
            self.c_exon_4_start = fnone(gd.c_exon_4_start)
            self.c_exon_4_end = fnone(gd.c_exon_4_end)
            self.c_exon_5_start = fnone(gd.c_exon_5_start)
            self.c_exon_5_end = fnone(gd.c_exon_5_end)
            self.c_exon_6_start = fnone(gd.c_exon_6_start)
            self.c_exon_6_end = fnone(gd.c_exon_6_end)
            self.c_exon_7_start = fnone(gd.c_exon_7_start)
            self.c_exon_7_end = fnone(gd.c_exon_7_end)
            self.c_exon_8_start = fnone(gd.c_exon_8_start)
            self.c_exon_8_end = fnone(gd.c_exon_8_end)
            self.c_exon_9_start = fnone(gd.c_exon_9_start)
            self.c_exon_9_end = fnone(gd.c_exon_9_end)

        self.unrearranged_support = []
        for gen in gd.genomic_accessions:
            self.unrearranged_support.append({
                'sequence_id': str(gen.id),
                'sequence': gen.sequence,
                'repository_name': fnone(gen.repository),
                'repository_ref': fnone(gen.accession),
                'patch_no': fnone(gen.patch_no),
                'gff_seqid': fnone(gen.gff_seqid),
                'gff_start': fnone(gen.sequence_start),
                'gff_end': fnone(gen.sequence_end),
                'strand': None if not gen.sense else ('+' if gen.sense.lower == 'forward' else '-' if gen.sense.lower == 'reverse' else None)
            })

        self.rearranged_support = []
        for rearr in gd.inferred_sequences:
            self.rearranged_support.append({
                'sequence_id': str(rearr.id),
                'sequence': rearr.sequence_details.nt_sequence,
                'derivation': None,
                'observation_type': 'inference from repertoire',
                'repository_name': fnone(rearr.submission.repertoire[0].repository_name),
                'repository_ref': fnone(rearr.seq_accession_no),
                'deposited_version': fnone(rearr.deposited_version),
                'sequence_start': 1,
                'sequence_end': len(rearr.sequence_details.nt_sequence),
            })

        self.paralogs = []
        if gd.paralogs and len(gd.paralogs) > 0:
            self.paralogs = gd.paralogs.split(',')
        self.paralogs = fnone(self.paralogs)

        self.curation = fnone(gd.notes)
        self.curational_tags = [enum_choice(x, ['likely_truncated', 'likely_full_length']) for x in gd.curational_tags.split(',')] if gd.curational_tags else []
        self.curational_tags = fnone(self.curational_tags)


class AIRRGermlineSet:
    def __init__(self, gs, gds, taxonomy=0):
        self.germline_set_id = 'OGRDB:' + gs.germline_set_id
        self.author = fnone(gs.author)
        self.lab_name = fnone(gs.lab_name)
        self.lab_address = fnone(gs.lab_address)
        self.acknowledgements = []
        for ack in gs.acknowledgements:
            self.acknowledgements.append({
                'acknowledgement_id': str(ack.id),
                'name': ack.ack_name,
                'institution_name': ack.ack_institution_name,
                'ORCID_id': ack.ack_ORCID_id
            })
        self.acknowledgements = fnone(self.acknowledgements)
        self.release_version = fnone(gs.release_version)
        self.release_description = fnone(gs.release_description)
        self.release_date = fnone(gs.release_date)
        self.germline_set_name = fnone(gs.germline_set_name)
        self.germline_set_ref = 'OGRDB:' + gs.germline_set_name + '.' + str(gs.release_version)
        self.pub_ids = []
        for pub_id in gs.pub_ids:
            self.pub_ids.append('PMID:' + pub_id.pubmed_id)
        self.pub_ids = fnone(','.join(self.pub_ids))
        self.species = {'id': f'NCBITAXON:{taxonomy}', 'label': gs.species}
        self.species_subgroup = fnone(gs.species_subgroup)
        self.species_subgroup_type = enum_choice(gs.species_subgroup_type, ['breed', 'strain', 'inbred', 'outbred', 'locational'])
        self.locus = enum_choice(gs.locus, ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG'])
        self.allele_descriptions = fnone(gds)
        self.curation = ''
        if len(gs.notes_entries) > 0:
            self.curation = gs.notes_entries[0].notes_text
        self.curation = fnone(self.curation)
