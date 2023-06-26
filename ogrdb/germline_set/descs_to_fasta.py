import re
from sequence_format import format_fasta_sequence


def descs_to_fasta(descs, format, fake_allele=False, extend=False):
    ret = ''
 
    gds = []
    if extend:
        sequences = {}
        for gd in descs:
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
        gds = descs

    gds.sort(key=lambda x: x.sequence_name)

    for desc in gds:
        name = desc.sequence_name

        if fake_allele:
            if '*' not in name:
                name += '*00'
            if name[4] == '-':
                name = name.replace('-', '0-')

        coding_seq = desc.coding_seq_imgt

        if 'ungapped' not in format:
            # remove trailing gaps
            cs = coding_seq
            while cs[-1] == '.':
                cs = cs[:-1]
            if extend and desc.ext_3prime:
                cs += desc.ext_3prime
            ret += format_fasta_sequence(name, cs, 60)
        else:
            seq = coding_seq.replace('.','')
            seq = seq.replace('-','')
            if extend and desc.ext_3prime:
                seq += desc.ext_3prime
            ret += format_fasta_sequence(name, seq, 60)
    return ret