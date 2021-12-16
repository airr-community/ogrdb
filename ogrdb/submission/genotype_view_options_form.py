# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from wtforms.validators import NumberRange
from wtforms import SubmitField, DecimalField, IntegerField, BooleanField

class GenotypeViewOptionsForm(FlaskForm):
    freq_threshold = DecimalField('Frequency Threshold', [NumberRange(min=0.0, max=100.0)], description="Only show alleles with unmutated frequency at least", places=2, default=0.0)
    occ_threshold = IntegerField('Sequences Threshold', [NumberRange(min=0)], description="Only show alleles with sequence count at least", default=0)
    sub_only = BooleanField('Submitted Inferences Only', description="Only show inferred alleles submitted for review")
    update = SubmitField('Filter')

