from sequence_format import *

from db.genotype_db import Genotype_table, make_Genotype_table
from db.styled_table import *


class SeqCol(StyledCol):
    def td_contents(self, item, attr_list):
        return '<button type="button" class="btn btn-xs btn-info" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
               % (format_nuc_sequence(item.nt_sequence, 50), item.sequence_id, format_fasta_sequence(item.sequence_id, item.nt_sequence, 50))


def setup_gv_table(desc):
    table = make_Genotype_table(desc.genotypes, False, classes = ['table-bordered'])
    table.add_column('nt_sequence', SeqCol('Sequence'))
    return table
