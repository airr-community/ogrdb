# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Form for sequence table selection

from wtforms import SelectField, SubmitField
from flask_wtf import FlaskForm


class SequenceTableForm(FlaskForm):
    species = SelectField('Species', description="Species for which the sequence table should be displayed")
    species_subgroup = SelectField('Subtype', description="Species subtype (if applicable)", validate_choice=False)
    locus = SelectField('Locus', description="Gene locus", validate_choice=False)
    submit = SubmitField('Show Sequences')