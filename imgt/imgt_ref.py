# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Check for new versions of the IMGR reference set, log changes and update the version used by Ogre


from Bio import SeqIO
import yaml


def read_reference(filename, species):
    records = {}

    for sp in species:
        records[sp] = {}

    for rec in SeqIO.parse(filename, 'fasta'):
        rd = rec.description.split('|')
        if rd[2] in species and rd[4] in ['V-REGION', 'D-REGION', 'J-REGION']:
            records[rd[2]][rd[1]] = rec.seq

    return records


def init_imgt_ref():
    with open('imgt/track_imgt_config.yaml', 'r') as fc:
        config = yaml.load(fc)

    species = config['species']
    recs = read_reference('static/docs/IMGT_REF.fasta', species)

    #
    # Fudge for species names used in OGRDB
    #

    recs['Human'] = recs['Homo sapiens']
    return recs

