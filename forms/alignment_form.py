# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class AlignmentForm(FlaskForm):
    species = SelectField('Species', validators=[DataRequired()], choices=[])
    locus = SelectField('Locus', validators=[DataRequired()], choices=[])
    gene_name = SelectField('Gene Name', validators=[DataRequired()], choices=[])
    submit = SubmitField('Show Alignments')
