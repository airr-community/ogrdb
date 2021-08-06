# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from custom_validators import *
from wtforms import SelectMultipleField, SubmitField


class NewGermlineSetGeneForm(FlaskForm):
    gene_description_id = SelectMultipleField('Gene', description="Select the gene to be added (use Ctr-click to select multiple genes", coerce=int)
    add = SubmitField('Add')
    create = SubmitField('Create')
    cancel = SubmitField('Cancel')
