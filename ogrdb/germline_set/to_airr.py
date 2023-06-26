# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import json
import re

# Create AIRR representation of items defined in the schema


def germline_set_to_airr(germline_set, extend):
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
                if int(re.sub(r"[^0-9]", "", gd.gene_subgroup)) < lowest_subgroup:
                    lowest_subgroup = int(re.sub(r"[^0-9]", "", gd.gene_subgroup))
                    rep = gd
            gds.append(rep)
    else:
        gds.extend(germline_set.gene_descriptions)

    ad = []
    for desc in gds:
        ad.append(vars(AIRRAlleleDescription(desc, extend)))

    gs = {'GermlineSet': [vars(AIRRGermlineSet(germline_set, ad))]}

    if extend:
        gs['GermlineSet'][0]['germline_set_name'] += '_extended'

    return gs


# Python-based ranges of IMGT elements
# <---------------------------------- FR1-IMGT -------------------------------->______________ CDR1-IMGT ___________<-------------------- FR2-IMGT ------------------->___________ CDR2-IMGT ________<----------------------------------------------------- FR3-IMGT ----------------------------------------------------> CDR3-IMGT
imgt_fr1 = (0, 78)
imgt_cdr1 = (78, 114)
imgt_fr2 = (114, 165)
imgt_cdr2 = (165, 195)
imgt_fr3 = (195, 312)


# Determine co-ordinates of IMGT-numbered elements in an ungapped sequence, given the gapped sequence
def delineate_v_gene(seq):
    coords = {}

    if seq[0] == '.':
        coords['fwr1_start'] = ''     # FWR start
        coords['fwr1_end'] = ''     # FWR1 stop
        coords['cdr1_start'] = ''      # CDR1 start
        coords['cdr1_end'] = ''      # CDR1 end
        coords['fwr2_start'] = ''     # FWR2 start
        coords['fwr2_end'] = ''     # FWR2 end
        coords['cdr2_start'] = ''    # CDR2 start
        coords['cdr2_end'] = ''     # CDR2 end
        coords['fwr3_start'] = ''     # FWR3 start
        coords['fwr3_end'] = ''     # FWR3 end
        return coords       # not going to guess about 5' incomplete sequences
                            # can revisit if this ever becomes an issue
                                
    pos = 1
    coords['fwr1_start'] = str(pos)     # FWR start
    pos += len(seq[slice(*imgt_fr1)].replace('.', '')) - 1
    coords['fwr1_end'] = str(pos)     # FWR1 stop
    pos += 1
    coords['cdr1_start'] = str(pos)      # CDR1 start
    pos += len(seq[slice(*imgt_cdr1)].replace('.', '')) - 1
    coords['cdr1_end'] = str(pos)      # CDR1 end
    pos += 1
    coords['fwr2_start'] = str(pos)     # FWR2 start
    pos += len(seq[slice(*imgt_fr2)].replace('.', '')) - 1
    coords['fwr2_end'] = str(pos)      # FWR2 end
    pos += 1
    coords['cdr2_start'] = str(pos)     # CDR2 start
    pos += len(seq[slice(*imgt_cdr2)].replace('.', '')) - 1
    coords['cdr2_end'] = str(pos)     # CDR2 end
    pos += 1
    coords['fwr3_start'] = str(pos)     # FWR3 start
    pos += len(seq[slice(*imgt_fr3)].replace('.', '')) - 1
    coords['fwr3_end'] = str(pos)     # FWR3 end
    pos += 1
    coords['cdr3_start'] = str(pos)     # CDR3 start

    return coords



class AIRRAlleleDescription:
    def __init__(self, gd, extend):
        self.allele_description_id = 'OGRDB:' + gd.description_id
        
        if not gd.species_subgroup:
            self.allele_description_ref = f"OGRDB:{gd.species}:{gd.sequence_name}.{gd.release_version}{'_ext' if extend else ''}"
        else:
            self.allele_description_ref = f"OGRDB:{gd.species}/{gd.species_subgroup}_{gd.locus}:{gd.sequence_name}.{gd.release_version}{'_ext' if extend else ''}"
        
        self.maintainer = gd.maintainer
        self.acknowledgements = []
        for ack in gd.acknowledgements:
            self.acknowledgements.append({
                'acknowledgement_id': ack.id,
                'name': ack.ack_name,
                'institution_name': ack.ack_institution_name,
                'ORCID_id': ack.ack_ORCID_id
            })
        self.lab_address = gd.lab_address
        self.release_version = gd.release_version
        self.release_date = gd.release_date.strftime('%d-%b-%Y')
        self.release_description = gd.release_description
        self.label = gd.sequence_name
        self.sequence = gd.sequence
        self.coding_sequence = gd.coding_seq_imgt.replace('.', '')
        if extend and gd.ext_3prime:
            self.coding_sequence += gd.ext_3prime
        self.aliases = []
        if gd.alt_names and len(gd.alt_names) > 0:
            self.aliases = gd.alt_names.split(',')
        self.locus = gd.locus
        self.chromosome = gd.chromosome
        self.sequence_type = gd.sequence_type
        self.functional = 'F' in gd.functionality
        self.inference_type = gd.inference_type

        # TODO - move these properly into database fields
        if gd.species == 'Human':
            self.species = {'id': 'NCBITAXON:9606', 'label': 'Homo sapiens'}
        elif gd.species == 'Mouse':
            self.species = {'id': 'NCBITAXON:10090', 'label': 'Mus musculus'}
        else:
            self.species = {'id': 'NCBITAXON:??', 'label': gd.species}

        self.species_subgroup = gd.species_subgroup
        self.species_subgroup_type = gd.species_subgroup_type
        self.status = gd.status if gd.status != 'published' else 'active'
        self.gene_designation = gd.gene_subgroup
        self.subgroup_designation = gd.subgroup_designation
        self.allele_designation = gd.allele_designation
        self.allele_similarity_cluster_designation = ''
        self.allele_similarity_cluster_member_id = ''
        self.gene_start = gd.gene_start
        self.gene_end = gd.gene_end

        if self.sequence_type == 'V':
            self.utr_5_prime_start = gd.utr_5_prime_start
            self.utr_5_prime_end = gd.utr_5_prime_end
            self.leader_1_start = gd.leader_1_start
            self.leader_1_end = gd.leader_1_end
            self.leader_2_start = gd.leader_2_start
            self.leader_2_end = gd.leader_2_end
            self.v_rs_start = gd.v_rs_start
            self.v_rs_end = gd.v_rs_end

            cs = gd.coding_seq_imgt
            if extend and gd.ext_3prime:
                cs += gd.ext_3prime

            coords = delineate_v_gene(cs)
            self.v_gene_delineations = [{
                'sequence_delineation_id': "1",
                'delineation_scheme': 'IMGT',
                'unaligned_sequence': cs.replace('.', ''),
                'aligned_sequence': cs,
                'fwr1_start': coords['fwr1_start'],
                'fwr1_end': coords['fwr1_end'],
                'cdr1_start': coords['cdr1_start'],
                'cdr1_end': coords['cdr1_end'],
                'fwr2_start': coords['fwr2_start'],
                'fwr2_end': coords['fwr2_end'],
                'cdr2_start': coords['cdr2_start'],
                'cdr2_end': coords['cdr2_end'],
                'fwr3_start': coords['fwr3_start'],
                'fwr3_end': coords['fwr3_end'],
                'cdr3_start': coords['cdr3_start'],
                'alignment': [],
            }]
            for i in range(1, 105):
                self.v_gene_delineations[0]['alignment'].append('%d' % i)

        if self.sequence_type == 'D':
            self.d_rs_3_prime_start = gd.d_rs_3_prime_start
            self.d_rs_3_prime_end = gd.d_rs_3_prime_end
            self.d_rs_5_prime_start = gd.d_rs_5_prime_start
            self.d_rs_5_prime_end = gd.d_rs_5_prime_end

        if self.sequence_type == 'J':
            self.j_codon_frame = gd.j_codon_frame
            self.j_cdr3_end = gd.j_cdr3_end
            self.j_rs_start = gd.j_rs_start
            self.j_rs_end = gd.j_rs_end

        self.unrearranged_support = []
        for gen in gd.genomic_accessions:
            self.unrearranged_support.append({
                'sequence_id': gen.id,
                'sequence': gen.sequence,
                'notes': gen.notes,
                'repository_name': gen.repository,
                'assembly_id': gen.accession,
                'patch_no': gen.patch_no,
                'gff_seqid': gen.gff_seqid,
                'gff_start': gen.sequence_start,
                'gff_end': gen.sequence_end,
                'strand': gen.sense,
            })

        self.rearranged_support = []
        for rearr in gd.inferred_sequences:
            self.rearranged_support.append({
                'sequence_id': rearr.id,
                'sequence': rearr.sequence_details.nt_sequence,
                'derivation': '',
                'observation_type': 'Inference from repertoire',
                'notes': '',
                'repository_name': rearr.submission.repertoire[0].repository_name,
                'repository_id': rearr.seq_accession_no,
                'deposited_version': rearr.deposited_version,
                'seq_start': 1,
                'seq_end': len(rearr.sequence_details.nt_sequence),
            })

        self.paralogs = []
        if gd.paralogs and len(gd.paralogs) > 0:
            self.paralogs = gd.paralogs.split(',')

        self.curation = gd.notes
        self.curational_tags = gd.curational_tags


class AIRRGermlineSet:
    def __init__(self, gs, gds):
        self.germline_set_id = 'OGRDB:' + gs.germline_set_id
        self.author = gs.author
        self.lab_name = gs.lab_name
        self.lab_address = gs.lab_address
        self.acknowledgements = []
        for ack in gs.acknowledgements:
            self.acknowledgements.append({
                'acknowledgement_id': ack.id,
                'name': ack.ack_name,
                'institution_name': ack.ack_institution_name,
                'ORCID_id': ack.ack_ORCID_id
            })
        self.release_version = gs.release_version
        self.release_description = gs.release_description
        self.release_date = gs.release_date
        self.germline_set_name = gs.germline_set_name
        self.germline_set_ref = 'OGRDB:' + gs.germline_set_name + '.' + str(gs.release_version)
        self.pub_ids = []
        for pub_id in gs.pub_ids:
            self.pub_ids.append('PMID:' + pub_id.pubmed_id)
        self.pub_ids = ','.join(self.pub_ids)

        # TODO - move these properly into database fields
        if gs.species == 'Human':
            self.species = {'id': 'NCBITAXON:9606', 'label': 'Homo sapiens'}
        elif gs.species == 'Mouse':
            self.species = {'id': 'NCBITAXON:10090', 'label': 'Mus musculus'}
        else:
            self.species = {'id': 'NCBITAXON:??', 'label': gs.species}

        self.species_subgroup = gs.species_subgroup
        self.species_subgroup_type = gs.species_subgroup_type
        self.locus = gs.locus
        self.allele_descriptions = gds
        self.curation = ''
        if len(gs.notes_entries) > 0:
            self.curation = gs.notes_entries[0].notes_text
