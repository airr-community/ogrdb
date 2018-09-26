from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class GeneDescriptionNotesForm(FlaskForm):
    notes = TextAreaField('Notes', [], description="Notes")


