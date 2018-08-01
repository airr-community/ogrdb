# FlaskForm class definitions for Submission

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField
class SubmissionForm(FlaskForm):
    submission_id = StringField('submission_id')
    submission_date = DateField('submission_date')
    submission_status = SelectField('submission_status', choices=[('draft', 'draft'), ('received', 'received'), ('reviewing', 'reviewing'), ('complete', 'complete')])
    submitter_name = StringField('submitter_name')
    submitter_address = StringField('submitter_address')
    submitter_email = StringField('submitter_email')
    submitter_phone = StringField('submitter_phone')
    species = SelectField('species', choices=[('human', 'human'), ('mouse', 'mouse'), ('macaque', 'macaque')])
    population_ethnicity = StringField('population_ethnicity')


