# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from custom_validators import *
from wtforms import SelectField, SubmitField, StringField, validators


class ReviewVdjbaseForm(FlaskForm):
    species = SelectField('Species', description="Species for which the analysis should be conducted")
    locus = SelectField('Locus', choices=[('IGH', 'IGH')], description="Gene locus")
    close = SubmitField('Close')
