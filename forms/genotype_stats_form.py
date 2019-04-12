# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from wtforms.validators import NumberRange
from wtforms import SelectField, SubmitField, DecimalField, IntegerField, StringField, BooleanField
from db.styled_table import *
from flask_table import create_table
from imgt.imgt_ref import imgt_reference_genes

from genotype_stats import generate_stats

class GeneStatsForm(FlaskForm):
    species = SelectField('Species', description="Species for which the analysis should be conducted")
    locus = SelectField('Locus', choices=[('IGH', 'IGH')], description="Gene locus")
    sequence_type = SelectField('Sequence Type', choices=[('V', 'V')], description="Sequence type (V, D, J, CH1 ... CH4, Leader)")
    freq_threshold = DecimalField('Frequency Threshold', [NumberRange(min=0.0, max=100.0)], description="Minimum frequency of an allele in a genotype for it to be included", places=2, default=0.10)
    rare_genes = StringField('Low-Frequency Genes', description="Comma-separated list of genes known to be present at low frequency, for which a lower threshold should be applied", default='IGHV1-69-2, IGHV2-70D, IGHV3-43D, IGHV7-4-1')
    rare_threshold = DecimalField('Low-Frequency Threshold', [NumberRange(min=0.0, max=100.0)], description="Threshold to apply to identified low-frequency genes", places=2, default=0.05)
    very_rare_genes = StringField('Very Low-Frequency Genes', description="Comma-separated list of genes known to be present at a very low frequency, for which an even lower threshold should be applied", default='IGHV1-45, IGHV4-28')
    very_rare_threshold = DecimalField('Very Low-Frequency Threshold', [NumberRange(min=0.0, max=100.0)], description="Threshold to apply to identified very low-frequency genes", places=2, default=0.02)
    allelic_threshold = DecimalField('Minimum Allelic Percentage', [NumberRange(min=0.0, max=100.0)], description="Minimum % of unmutated sequences assigned to this allele as opposed to other alleles of the same gene", places=2, default=20.0)
    assigned_unmutated_threshold = DecimalField('Minimum Unmutated Percentage', [NumberRange(min=0.0, max=100.0)], description="Minimum % of sequences assigned to this allele that are unmutated", places=2, default=1.00)
    create = SubmitField('View Report')


class GeneStats_table(StyledTable):
    gene = StyledCol("Allele")
    occurrences = StyledCol("Occurrences", tooltip="Number of genotypes including the allele")
    unmutated_freq = StyledCol("Unmutated Frequency", tooltip="Unmutated frequency, averaged over all included genotypes")


def make_GeneStats_table_table(results, classes=()):
    t=create_table(base=GeneStats_table)
    ret = t(results, classes=classes)
    return ret



def setup_gene_stats_tables(form):
    ret = {}
    (ret['count'], stats, raw) = generate_stats(form)
    ret['raw'] = raw.getvalue()
    raw.close()

    if ret['count'] == 0:
        ret['gene_table'] = None
    else:
        ret['gene_table'] = make_GeneStats_table_table(stats)

    return ret

