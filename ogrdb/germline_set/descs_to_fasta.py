import re
from tkinter.font import names
from sequence_format import format_fasta_sequence


def descs_to_fasta(descs, format, fake_allele=False, extend=False):
    """
    Convert gene descriptions to FASTA format.
    
    Args:
        descs: List of gene description objects containing sequence information
        format: Format specification string. If 'ungapped' is in the string, gaps will be removed
        fake_allele: If True, adds fake allele designations (*00) to sequence names lacking them
        extend: If True, groups sequences by coding_seq_imgt and selects representatives,
                extending sequences with 3' extensions when available
    
    Returns:
        String containing FASTA-formatted sequences with 60-character line width
        
    Notes:
        - When extend=True, selects one representative per sequence group based on:
          1. paralog_rep flag (if present)
          2. Lowest gene_subgroup number
          3. First sequence name alphabetically
        - Removes trailing gaps from gapped sequences
        - Skips sequences with empty coding_seq_imgt
    """
    ret = ''
 
    gds = []
    sc_gds = []
    if extend:
        sequences = {}
        for gd in descs:
            if gd.coding_seq_imgt not in sequences:
                sequences[gd.coding_seq_imgt] = []
            sequences[gd.coding_seq_imgt].append(gd)
            if gd.secretory_coding_sequence:
                if 'SC' + gd.secretory_coding_sequence not in sequences:
                    sequences['SC' + gd.secretory_coding_sequence] = []
                sequences['SC' + gd.secretory_coding_sequence].append(gd)

        for sequence, gd_group in sequences.items():
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

            if sequence.startswith('SC'):
                sc_gds.append(rep)
            else:
                gds.append(rep)

            if len(gd_group) > 1:
                rep = None
                for gd in gd_group:
                    if gd.paralog_rep:
                        rep = gd
                        break
                if not rep:
                    print(f"No rep found for {', '.join([gd.sequence_name for gd in gd_group])}")

    else:
        gds = descs

        for gd in gds:
            if gd.secretory_coding_sequence:
                sc_gds.append(gd)

    gds.sort(key=lambda x: x.sequence_name)
    sc_gds.sort(key=lambda x: x.sequence_name)

    for desc in gds:
        name = desc.sequence_name

        if fake_allele:
            if '*' not in name:
                name += '*00'
            if name[4] == '-':
                name = name.replace('-', '0-')

        coding_seq = desc.coding_seq_imgt
        if len(coding_seq) == 0:
            print(f'No coding sequence for {desc.sequence_name}')
            continue

        if 'ungapped' not in format:
            # remove trailing gaps
            cs = coding_seq
            while cs[-1] == '.':
                cs = cs[:-1]
            if extend and desc.ext_3prime:
                cs += desc.ext_3prime
            ret += format_fasta_sequence(name, cs, 60)
        else:
            seq = coding_seq.replace('.', '')
            seq = seq.replace('-', '')
            if extend and desc.ext_3prime:
                seq += desc.ext_3prime
            ret += format_fasta_sequence(name, seq, 60)

    for desc in sc_gds:
        name = desc.sequence_name

        if fake_allele:
            if '*' not in name:
                name += '*00'
            if name[4] == '-':
                name = name.replace('-', '0-')

        coding_seq = desc.secretory_coding_sequence
        if len(coding_seq) == 0:
            print(f'No secretory coding sequence for {desc.sequence_name}')
            continue

        seq = coding_seq.replace('.', '')
        seq = seq.replace('-', '')
        ret += format_fasta_sequence(name + '_SC', seq, 60)
        
    return ret