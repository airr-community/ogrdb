# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Read the reference set downloaded from IMGT
# Read human alleles downloaded from IGPDB


from Bio import SeqIO
import yaml

imgt_reference_genes = {}
igpdb_genes = {}

def read_reference(filename, species):
    records = {}

    for sp in species:
        records[sp] = {}

    for rec in SeqIO.parse(filename, 'fasta'):
        rd = rec.description.split('|')
        if rd[2] in species and rd[4] in ['V-REGION', 'D-REGION', 'J-REGION']:
            records[rd[2]][rd[1]] = rec.seq.lower()

    return records


def init_imgt_ref():
    global imgt_reference_genes

    with open('imgt/track_imgt_config.yaml', 'r') as fc:
        config = yaml.load(fc)

    species = config['species']
    imgt_reference_genes = read_reference('static/docs/IMGT_REF.fasta', species)

    #
    # Fudge for species names used in OGRDB
    #

    imgt_reference_genes['Human'] = imgt_reference_genes['Homo sapiens']
    imgt_reference_genes['Test'] = imgt_reference_genes['Homo sapiens']

def imgt_reference_genes():
    global imgt_reference_genes
    return imgt_reference_genes

def init_igpdb_ref():
    global igpdb_genes
    igpdb_genes = {}

    for rec in SeqIO.parse('static/docs/igpdb.fasta', 'fasta'):
        rd = rec.description.split('|')
        igpdb_genes[rd[0]] = rec.seq.lower()

def igpdb_ref():
    global igpdb_genes
    return igpdb_genes

