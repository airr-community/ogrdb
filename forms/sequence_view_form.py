

from db.gene_description_db import *
from db.repertoire_db import make_Acknowledgements_table
from db.inferred_sequence_table import MessageHeaderCol, MessageBodyCol, setup_inferred_sequence_table
from sequence_format import *
from copy import deepcopy
from textile import textile


class GeneDescriptionNotes_table(StyledTable):
    id = Col("id", show=False)
    notes = StyledCol("Notes", tooltip="Notes")


def make_GeneDescriptionNotes_table(results, private = False, classes=()):
    t=create_table(base=GeneDescriptionNotes_table)
    ret = t(results, classes=classes)
    return ret


def setup_sequence_view_tables(db, seq):
    tables = {}
    tables['gene_description'] = make_GeneDescription_view(seq)

    if seq.inference_type == 'Rearranged Only':
        wanted = []
    else:
        wanted = ['l_region_start', 'l_region_end']

        if seq.domain == 'V':
            wanted.extend(['v_rs_start', 'v_rs_end', 'utr_5_prime_start', 'utr_5_prime_end', 'start_5prime_ext', 'end_5prime_ext'])
        elif seq.domain == 'D':
            wanted.extend(['d_rs_3_prime_start', 'd_rs_3_prime_end', 'd_rs_5_prime_start', 'd_rs_5_prime_end'])
        elif seq.domain == 'J':
            wanted.extend(['j_rs_start', 'j_rs_end'])

    if seq.domain == 'J':
        wanted.extend(['j_cdr3_end', 'codon_frame'])

    optional_fields = ['l_region_start', 'l_region_end', 'utr_5_prime_start', 'utr_5_prime_end', 'start_5prime_ext', 'end_5prime_ext',
                  'v_rs_start', 'v_rs_end', 'd_rs_3_prime_start', 'd_rs_3_prime_end', 'd_rs_5_prime_start', 'd_rs_5_prime_end',
                  'j_rs_start', 'j_rs_end', 'j_cdr3_end', 'codon_frame']

    fields = deepcopy(tables['gene_description'].items)
    for field in fields:
        if field['field'] in optional_fields and field['field'] not in wanted:
            tables['gene_description'].items.remove(field)

    for field in tables['gene_description'].items:
        if field['field'] == 'sequence':
            if field['value'] is not None and len(field['value']) > 0:
                field['value'] =  Markup('<button type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
                    % (format_nuc_sequence(seq.sequence, 50), seq.sequence_name, format_fasta_sequence(seq.sequence_name, seq.sequence, 50)))
            else:
                field['value'] = 'None'
        elif field['field'] == 'coding_seq_imgt':
            if field['value'] is not None and len(field['value']) > 0:
                if seq.domain == 'V':
                    field['value'] =  Markup('<button type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
                        % (format_imgt_v(seq.coding_seq_imgt, 52), seq.sequence_name, format_fasta_sequence(seq.sequence_name, seq.coding_seq_imgt, 50)))
                else:
                    field['value'] =  Markup('<button type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s"><span class="glyphicon glyphicon-search" data-toggle="tooltip" title="View"></span>&nbsp;</button>' \
                        % (format_nuc_sequence(seq.sequence, 50), seq.sequence_name, format_fasta_sequence(seq.sequence_name, seq.sequence, 50)))
            else:
                field['value'] = 'None'
        elif field['field'] == 'release_description':
            if field['value'] is not None and len(field['value']) > 0:
                field['value'] = Markup(textile(field['value']))

    tables['inferred_sequences'] = setup_inferred_sequence_table(seq.inferred_sequences, seq.id, action=False)
    tables['acknowledgements'] = make_Acknowledgements_table(seq.acknowledgements)
    tables['notes'] = make_GeneDescriptionNotes_table([{'notes': Markup(textile(seq.notes)), 'id': seq.id}])

    history = db.session.query(JournalEntry).filter_by(gene_description_id = seq.id, type = 'history').all()
    tables['history'] = []

    for entry in history:
        t = StyledTable([entry], classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['history'].append(t)

    return tables

