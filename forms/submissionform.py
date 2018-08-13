
# FlaskForm class definitions for Submission

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class SubmissionForm(FlaskForm):
    submission_id = StringField('submission_id', [validators.Length(max=255)])
    submission_date = DateField('submission_date')
    submission_status = SelectField('submission_status', choices=[('draft', 'draft'), ('reviewing', 'reviewing'), ('published', 'published'), ('complete', 'complete')])
    submitter_name = StringField('submitter_name', [validators.Length(max=255)])
    submitter_address = StringField('submitter_address', [validators.Length(max=255)])
    submitter_email = StringField('submitter_email', [validators.Length(max=255)])
    submitter_phone = StringField('submitter_phone', [validators.Length(max=40)])
    species = SelectField('species')
    population_ethnicity = StringField('population_ethnicity', [validators.Length(max=255)])


