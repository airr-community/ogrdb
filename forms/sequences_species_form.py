# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Form for species download selection

from wtforms import BooleanField, SelectField
from flask_wtf import FlaskForm


class SpeciesForm(FlaskForm):
    species = SelectField('Species', description="Species for which the analysis should be conducted")
    exclude_imgt = BooleanField('Only include alleles that are not in IMGT/Gene-DB')

