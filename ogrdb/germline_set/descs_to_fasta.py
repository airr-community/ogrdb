from sequence_format import format_fasta_sequence


def descs_to_fasta(descs, format):
    ret = ''
    for desc in descs:
        name = desc.sequence_name
        if desc.imgt_name != '':
            name += '|IMGT=' + desc.imgt_name
        if format == 'gapped':
            ret += format_fasta_sequence(name, desc.coding_seq_imgt, 60)
        else:
            seq = desc.coding_seq_imgt.replace('.','')
            seq = seq.replace('-','')
            ret += format_fasta_sequence(name, seq, 60)
    return ret