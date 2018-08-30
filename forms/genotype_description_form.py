
# FlaskForm class definitions for GenotypeDescription

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class GenotypeDescriptionForm(FlaskForm):
    genotype_name = StringField('Genotype Name', [validators.Length(max=255), NonEmpty()], description="Descriptive name for this genotype")
    genotype_subject_id = StringField('Subject ID', [validators.Length(max=255)], description="Identifier of the subject from which this genotype was inferred")
    genotype_biosample_ids = StringField('Sample IDs', [validators.Length(max=255)], description="Comma-separated list of accession number(s) of the sample(s) from which the genotype was derived (e.g. NIH biosamples or ENA samples)")
    genotype_filename = StringField('Genotype Filename', [validators.Length(max=255)], description="Name of the uploaded file from which the genotype was read")
    genotype_file = FileField('Genotype File', description="Contents of the uploaded file from which the genotype was read")
    inference_tool_id = SelectField('Inference Tool', [validators.Optional()], choices=[])


