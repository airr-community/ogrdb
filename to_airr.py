# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Create AIRR representation of items defined in the schema


class AIRRGeneDescription:
    def __init__(self, gd):
        self.gene_description_id = 'OGRDB:' + gd.description_id
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
        self.release_date = gd.release_date
        self.gene_symbol = gd.sequence_name
        self.sequence = gd.sequence
        self.coding_sequence = gd.coding_seq_imgt
        self.coding_sequence_identifier = gd.coding_sequence_identifier
        self.alt_names = []
        if gd.alt_names and len(gd.alt_names) > 0:
            self.alt_names = gd.alt_names.split(',')
        self.locus = gd.locus
        self.chromosome = gd.chromosome
        self.sequence_type = gd.sequence_type
        self.functional = gd.functional
        self.inference_type = gd.inference_type
        self.species = gd.species
        self.species_subgroup = gd.species_subgroup
        self.species_subgroup_type = gd.species_subgroup_type
        self.status = gd.status if gd.status != 'published' else 'active'
        self.gene_subgroup = gd.gene_subgroup
        self.subgroup_designation = gd.subgroup_designation
        self.allele_designation = gd.allele_designation
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
            self.v_gene_delineations = [{
                'germline_delineation_id': 1,
                'delineation_scheme': 'IMGT',
                'fwr1_start': 1,
                'fwr1_end': 78,
                'cdr1_start': 79,
                'cdr1_end': 114,
                'fwr2_start': 115,
                'fwr2_end': 165,
                'cdr2_start': 166,
                'cdr2_end': 195,
                'fwr3_start': 196,
                'fwr3_end': 312,
                'cdr3_start': 313,
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
            self.j_rs_end = gd.v
            self.j_donor_splice = gd.j_donor_splice

        self.genomic_support = []
        for gen in gd.genomic_accessions:
            self.genomic_support.append({
                'sequence_id': gen.id,
                # Current AIRR schema has 'sequence' rather than co-ordinates
                'sequence_start': gen.sequence_start,
                'sequence_end': gen.sequence_end,
                'notes': '',
                'repository_name': gen.repository,
                'assembly_id': gen.accession,
                'patch_no': '',
                'gff_seqid': '',
                'gff_start': '',
                'gff_end': '',
                'strand': ''
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

        self.notes = gd.notes
        self.curational_tags = gd.curational_tags
