# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Calculate statistics based on published genotypes

from collections import OrderedDict
from Bio import SeqIO
from io import StringIO
import csv

from app import db
from db.submission_db import *
from db.gene_description_db import *
from imgt.imgt_ref import get_imgt_reference_genes


def parse_name(name):
    allele_designation = ''
    subgroup_designation = ''
    gene_subgroup = ''
    sn = name

    if '-' in sn:
        if '*' in sn:
            snq = sn.split('*')
            allele_designation = snq[1]
            sn = snq[0]
        else:
            allele_designation = ''
        snq = sn.split('-')
        subgroup_designation = snq[len(snq)-1]
        del(snq[len(snq)-1])
        gene_subgroup = '-'.join(snq)[4:]
    elif '*' in sn:
        snq = sn.split('*')
        gene_subgroup = snq[0][4:]
        allele_designation = snq[1]
    else:
        gene_subgroup = sn[4:]

    if len(subgroup_designation) == 1:
        subgroup_designation = '0' + subgroup_designation

    if len(allele_designation) == 1:
        allele_designation = '0' + allele_designation

    return(gene_subgroup, subgroup_designation, allele_designation)


def generate_stats(form):
    species = form.species.data
    locus = form.locus.data
    sequence_type = form.sequence_type.data

    imgt_ref = get_imgt_reference_genes()
    if species not in imgt_ref:
        return (0, None, None)

    def gene_match(gene, ref):
        for k,v in ref.items():
            if gene in k:
                return True
        return False

    rare_genes = form.rare_genes.data.replace(' ', '').split(',')
    rare_missing = []
    for gene in rare_genes:
        if not gene_match(gene, imgt_ref[species]):
            rare_missing.append(gene)
    if len(rare_missing) > 0:
        form.rare_genes.errors = ['Gene(s) %s not found in IMGT reference database' % ', '.join(rare_missing)]

    very_rare_genes = form.very_rare_genes.data.replace(' ', '').split(',')
    very_rare_missing = []
    for gene in very_rare_genes:
        if not gene_match(gene, imgt_ref[species]):
            very_rare_missing.append(gene)
    if len(very_rare_missing) > 0:
        form.very_rare_genes.errors = ['Gene(s) %s not found in IMGT reference database' % ', '.join(very_rare_missing)]

    if len(rare_missing) > 0 or len(very_rare_missing) > 0:
        return (0, None, None)

    ref = []

    for gene in imgt_ref[species].keys():
        if locus in gene and gene[3] == sequence_type:
            ref.append(gene)

    # Calculate thresholds for each reference gene

    gene_thresh = {}

    for gene in imgt_ref[species].keys():
        gene_thresh[gene] =  form.freq_threshold.data
        for rg in rare_genes:
            if rg in gene:
                gene_thresh[gene] = form.rare_threshold.data
        for rg in very_rare_genes:
            if rg in gene:
                gene_thresh[gene] = form.very_rare_threshold.data

    # Get unique list of genotype descriptions that underlie affirmed inferences

    genotype_descriptions = []
    seqs = db.session.query(GeneDescription).filter(GeneDescription.status == 'published',
                                                    GeneDescription.organism == species,
                                                    GeneDescription.locus == locus,
                                                    GeneDescription.sequence_type == sequence_type,
                                                    GeneDescription.affirmation_level != '0'
                                                    ).all()

    for seq in seqs:
        for genotype in seq.inferred_sequences:
            if genotype.genotype_description not in genotype_descriptions:
                genotype_descriptions.append(genotype.genotype_description)

    if len(genotype_descriptions) == 0:
        return (0, None, None)

    # Initialise stats

    stats = {}
    for name in ref:
        if '/OR' not in name:
            stats[name] = {'occurrences': 0, 'unmutated_freq': [], 'gene': name}

    stats = OrderedDict(sorted(stats.items(), key=lambda name: parse_name(name[0])[2]))
    stats = OrderedDict(sorted(stats.items(), key=lambda name: parse_name(name[0])[1]))
    stats = OrderedDict(sorted(stats.items(), key=lambda name: parse_name(name[0])[0]))

    raw = {}
    for name in ref:
        if '/OR' not in name:
            raw[name] = {'gene': name}

    raw = OrderedDict(sorted(raw.items(), key=lambda name: parse_name(name[0])[2]))
    raw = OrderedDict(sorted(raw.items(), key=lambda name: parse_name(name[0])[1]))
    raw = OrderedDict(sorted(raw.items(), key=lambda name: parse_name(name[0])[0]))

    # Compose stats

    gen_names = ['gene']

    for desc in genotype_descriptions:
        gen_name = "%s/%s" % (desc.submission.submission_id, desc.genotype_name)
        gen_names.append(gen_name)
        for gen in desc.genotypes:
            if gen.sequence_id in stats \
              and (gen.allelic_percentage is None or gen.allelic_percentage==0 or gen.allelic_percentage >= form.allelic_threshold.data) \
              and (gen.assigned_unmutated_frequency is None or gen.assigned_unmutated_frequency >= form.assigned_unmutated_threshold.data) \
              and (gen.unmutated_frequency is not None and gen.unmutated_frequency >= gene_thresh[gen.sequence_id]):
                stats[gen.sequence_id]['occurrences'] += 1
                stats[gen.sequence_id]['unmutated_freq'].append(gen.unmutated_frequency)
            if gen.sequence_id in raw and (gen.allelic_percentage is None or gen.allelic_percentage >= form.allelic_threshold.data):
                raw[gen.sequence_id][gen_name] = gen.unmutated_frequency

    for (k, stat) in stats.items():
        stats[k]['unmutated_freq'] = round(sum(stat['unmutated_freq'])/max(len(stat['unmutated_freq']),1), 2)

    ret = []
    for(k, stat) in stats.items():
        ret.append(stat)

    ro = StringIO()
    writer = csv.DictWriter(ro, fieldnames=gen_names)
    writer.writeheader()
    for gene in raw:
        writer.writerow(raw[gene])

    return (len(genotype_descriptions), ret, ro)

