# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from wtforms.validators import NumberRange
from wtforms import SelectField, SubmitField, DecimalField, IntegerField
from db.styled_table import *
from flask_table import create_table

from genotype_stats import generate_stats

class GeneStatsForm(FlaskForm):
    species = SelectField('Species', description="Species for which the analysis should be conducted")
    locus = SelectField('Locus', choices=[('IGH', 'IGH')], description="Gene locus")
    sequence_type = SelectField('Sequence Type', choices=[('V', 'V')], description="Sequence type (V, D, J, CH1 ... CH4, Leader)")
    freq_threshold = DecimalField('Frequency Threshold', [NumberRange(min=0.0, max=100.0)], description="Minimum frequency of an allele in a genotype for it to be included", places=2, default=0.0)
    occ_threshold = IntegerField('Occurrences Threshold', [NumberRange(min=0)], description="Minimum number of occurrences for an allele to be displayed", default=0)
    create = SubmitField('View Report')


class GeneStats_table(StyledTable):
    gene = StyledCol("Allele")
    occurrences = StyledCol("Occurrences", tooltip="Number of genotypes including the allele")
    unmutated_freq = StyledCol("Unmutated Frequency", tooltip="Unmutated frequency, averaged over all including genotypes")


def make_GeneStats_table_table(results, classes=()):
    t=create_table(base=GeneStats_table)
    ret = t(results, classes=classes)
    return ret


def setup_gene_stats_tables(species, locus, sequence_type, min_freq, min_occ):
    ret = {}
    (ret['count'], stats) = generate_stats(species, locus, sequence_type, min_freq, min_occ)

    if ret['count'] == 0:
        ret['gene_table'] = None
    else:
        ret['gene_table'] = make_GeneStats_table_table(stats)

    return ret

