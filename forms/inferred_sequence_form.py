
# FlaskForm class definitions for InferredSequence

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class InferredSequenceForm(FlaskForm):
    sequence_id = SelectField('sequence_id', [validators.Optional()], choices=[])
    genotype_id = SelectField('genotype_id', [validators.Optional()], choices=[])
    repository_id = StringField('repository_id', [validators.Length(max=255)])
    deposited_version = StringField('deposited_version', [validators.Length(max=255)])
    run_ids = StringField('run_ids', [validators.Length(max=255)])


