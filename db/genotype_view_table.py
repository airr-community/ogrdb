
from db.genotype_db import Genotype_table, make_Genotype_table
from db.styled_table import *

class SeqCol(StyledCol):
    def td_contents(self, item, attr_list):
        return '<button type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
               % (format_nuc_sequence(item.nt_sequence, 50), item.sequence_id, format_fasta_sequence(item.sequence_id, item.nt_sequence, 50))

def setup_gv_table(desc):
    table = make_Genotype_table(desc.genotypes, False, classes = ['table-bordered'])
    table.rotate_header = True
    table.add_column('nt_sequence', SeqCol('Sequence', tooltip="Click to view or download sequence"))
    return table

def setup_gv_fasta(desc):
    f = ''
    for g in desc.genotypes:
        f += format_fasta_sequence(g.sequence_id, g.nt_sequence, 100)
    return f