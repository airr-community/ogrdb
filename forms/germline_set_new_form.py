# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from custom_validators import *
from wtforms import SelectField, SubmitField, StringField, validators


class NewGermlineSetForm(FlaskForm):
    name = StringField('New Set Name', description="The name for this new germline set")
    locus = SelectField('Locus', description="Locus")
    create = SubmitField('Create')
    cancel = SubmitField('Cancel')
