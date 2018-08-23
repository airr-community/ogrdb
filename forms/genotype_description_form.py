
# FlaskForm class definitions for GenotypeDescription

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class GenotypeDescriptionForm(FlaskForm):
    genotype_name = StringField('genotype_name', [validators.Length(max=255), NonEmpty()])
    genotype_subject_id = StringField('genotype_subject_id', [validators.Length(max=255)])
    genotype_biosample_ids = StringField('genotype_biosample_ids', [validators.Length(max=255)])
    genotype_filename = StringField('genotype_filename', [validators.Length(max=255)])
    genotype_file = FileField('genotype_file')
    inference_tool_id = SelectField('inference_tool_id', [validators.Optional()], choices=[])


