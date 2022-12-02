from sequence_format import format_fasta_sequence


def descs_to_fasta(descs, format, fake_allele=False):
    ret = ''
    for desc in descs:
        name = desc.sequence_name

        if fake_allele:
            if '*' not in name:
                name += '*00'
            if name[4] == '-':
                name = name.replace('-', '0-')

        if format == 'gapped':
            ret += format_fasta_sequence(name, desc.coding_seq_imgt, 60)
        else:
            seq = desc.coding_seq_imgt.replace('.','')
            seq = seq.replace('-','')
            ret += format_fasta_sequence(name, seq, 60)
    return ret