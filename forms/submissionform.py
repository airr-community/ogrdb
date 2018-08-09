
# FlaskForm class definitions for Submission

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, validators
class SubmissionForm(FlaskForm):
    submission_id = StringField('submission_id')
    submission_date = DateField('submission_date')
    submission_status = SelectField('submission_status', choices=[('draft', 'draft'), ('reviewing', 'reviewing'), ('published', 'published'), ('complete', 'complete')])
    submitter_name = StringField('submitter_name')
    submitter_address = StringField('submitter_address')
    submitter_email = StringField('submitter_email')
    submitter_phone = StringField('submitter_phone')
    species = SelectField('species')
    population_ethnicity = StringField('population_ethnicity')


