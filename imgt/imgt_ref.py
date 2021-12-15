# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Read the reference set downloaded from IMGT
# Read human alleles downloaded from IGPDB


from Bio import SeqIO
import yaml
from head import app
import sys
import os.path
import pickle
import json

imgt_reference_genes = None
imgt_gapped_reference_genes = None
igpdb_genes = None
imgt_config = None

# indexed by species and then by codon (first codon = 1), lists the residues found in that location in the reference set
reference_v_codon_usage = None


# Read IMGT reference file and build the reference and codon usage data, using species defined in the config file
def init_imgt_ref():
    global imgt_reference_genes
    global imgt_gapped_reference_genes
    global reference_v_codon_usage
    global imgt_config

    with open('imgt/track_imgt_config.yaml', 'r') as fc:
        imgt_config = yaml.load(fc, Loader=yaml.FullLoader)
        if 'Test' not in imgt_config['species']:
            imgt_config['species']['Test'] = {'alias': 'Test'}

    species = imgt_config['species']

    imgt_reference_genes = None
    if os.path.exists(imgt_config['imgt_ref_pickle']) and max(os.path.getmtime('imgt/track_imgt_config.yaml'), os.path.getmtime(imgt_config['ogre_ref_file'])) < os.path.getmtime(imgt_config['imgt_ref_pickle']):
        try:
            imgt_reference_genes = pickle.load(open(imgt_config['imgt_ref_pickle'], "rb"))
        except:
            imgt_reference_genes = None
            app.logger.error("Error reading %s: rebuilding" % imgt_config['imgt_ref_pickle'])

    if imgt_reference_genes is None:
        try:
            imgt_reference_genes = read_reference(imgt_config['ogre_ref_file'], species)
            imgt_reference_genes['Test'] = imgt_reference_genes['Human']
            pickle.dump(imgt_reference_genes, open(imgt_config['imgt_ref_pickle'], "wb"))
        except:
            app.logger.error("Error parsing IMGT reference file: %s" % sys.exc_info()[0])

    imgt_gapped_reference_genes = None
    if os.path.exists(imgt_config['imgt_gapped_ref_pickle']) and max(os.path.getmtime('imgt/track_imgt_config.yaml'), os.path.getmtime(imgt_config['gapped_ogre_ref_file'])) < os.path.getmtime(imgt_config['imgt_gapped_ref_pickle']):
        try:
            imgt_gapped_reference_genes = pickle.load(open(imgt_config['imgt_gapped_ref_pickle'], "rb"))
        except:
            imgt_gapped_reference_genes = None
            app.logger.error("Error reading %s: rebuilding" % imgt_config['imgt_gapped_ref_pickle'])

    if imgt_gapped_reference_genes is None:
        try:
            imgt_gapped_reference_genes = read_reference(imgt_config['gapped_ogre_ref_file'], species)
            imgt_gapped_reference_genes['Test'] = imgt_gapped_reference_genes['Human']
            pickle.dump(imgt_gapped_reference_genes, open(imgt_config['imgt_gapped_ref_pickle'], "wb"))
        except:
            app.logger.error("Error parsing IMGT gapped file: %s" % sys.exc_info()[0])

    reference_v_codon_usage = None
    if os.path.exists(imgt_config['codon_usage_pickle']) and max(os.path.getmtime('imgt/track_imgt_config.yaml'), os.path.getmtime(imgt_config['ogre_ref_file'])) < os.path.getmtime(imgt_config['codon_usage_pickle']):
        try:
            reference_v_codon_usage = pickle.load(open(imgt_config['codon_usage_pickle'], "rb"))
        except:
            reference_v_codon_usage = None
            app.logger.error("Error reading %s: rebuilding" % imgt_config['codon_usage_pickle'])

    if reference_v_codon_usage is None:
        try:
            reference_v_codon_usage = {}

            for sp in imgt_gapped_reference_genes.keys():
                reference_v_codon_usage[sp] = {}
                for chain in 'IGHV', 'IGKV', 'IGLV':
                    reference_v_codon_usage[sp][chain] = find_codon_usage(imgt_gapped_reference_genes, sp, chain)

            pickle.dump(reference_v_codon_usage, open(imgt_config['codon_usage_pickle'], "wb"))
        except:
            app.logger.error("Error determining germline codon usage: %s" % sys.exc_info()[0])


def read_reference(filename, species):
    records = {}

    for sp in species.keys():
        for al in species[sp]['alias'].split(','):
            records[al] = {}

    for rec in SeqIO.parse(filename, 'fasta'):
        rd = rec.description.split('|')
        if rd[2] in species.keys() and (rd[4] in ['V-REGION', 'D-REGION', 'J-REGION']) and (rec.seq is not None):
            for al in species[rd[2]]['alias'].split(','):
                records[al][rd[1]] = rec.seq.lower()

    return records

def find_family(gene):
    if '-' not in gene:
        return None

    return gene.split('-')[0][4:]

# find the 1-based index of a nucleotide in a gapped reference sequence, given its index in the ungapped sequence
def find_gapped_index(ind_ungapped, species, gene_name):
    gapped_seq = list(imgt_gapped_reference_genes[species][gene_name])

    ind = 0
    found_nt = 0

    while found_nt < ind_ungapped:
        if gapped_seq[ind] != '.':
            found_nt += 1
        ind += 1

    return ind + 1

# Gap a sequence given the closest gapped reference

def gap_sequence(seq, ref):
    i_seq = iter(list(seq))
    i_ref = iter(list(ref))
    ret = ''

    # if reference is partial at the 5' end, pass nucleotides through until we reach the first 'real' reference position
    five_gapped = True

    try:
        while(True):
            r = next(i_ref)
            if r != '.':
                five_gapped = False
                ret += next(i_seq)
            else:
                if five_gapped:
                    ret += next(i_seq)
                else:
                    ret += '.'
    except StopIteration:
        pass

    # if the sequence is longer than the ref, need to add on trailing nucs

    try:
        while(True):
            ret += next(i_seq)
    except StopIteration:
        pass

    return ret

def find_codon_usage(gapped_reference_genes, species, chain):
    usage = {}

    for (gene_name, nt_seq) in gapped_reference_genes[species].items():
        if chain in gene_name:
            family = find_family(gene_name)
            if family not in usage:
                usage[family] = [[],]
            try:
                aa_seq = list(nt_seq.upper().translate(gap='.'))

                for i in range(0, len(aa_seq)):
                    if len(usage[family]) <= i+1:
                        usage[family].append([])
                    if aa_seq[i] not in usage[family][i+1]:
                        usage[family][i+1].append(aa_seq[i])
            except:
                pass
    return usage

def init_igpdb_ref():
    global igpdb_genes
    igpdb_genes = {}

    for rec in SeqIO.parse(os.path.join(imgt_config['update_file_dir'], 'igpdb.fasta'), 'fasta'):
        rd = rec.description.split('|')
        igpdb_genes[rd[0]] = str(rec.seq.lower())



# if we just import the global variables in another module, they are empty
# I suspect this is related to threading but it could be a basic coding error

def get_imgt_reference_genes():
    return imgt_reference_genes

def get_reference_v_codon_usage():
    return reference_v_codon_usage

def get_imgt_gapped_reference_genes():
    return imgt_gapped_reference_genes

def get_igpdb_ref():
    return igpdb_genes

def get_imgt_config():
    return imgt_config
