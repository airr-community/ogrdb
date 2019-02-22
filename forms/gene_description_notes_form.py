# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators, MultipleFileField
class GeneDescriptionNotesForm(FlaskForm):
    notes = TextAreaField('Notes', [], description="Notes")
    notes_attachment = MultipleFileField('Attachments', description="File attachments")


