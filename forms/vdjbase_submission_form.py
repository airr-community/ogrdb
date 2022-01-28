# FlaskForm class definition for sumbission_from_vdjbase

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *


from wtforms import StringField,  validators
class VdjbaseSubmissionForm(FlaskForm):
    sample_name = StringField('Sample Name', [validators.Length(max=255)], description="Sample name in VDJbase")
    submission_id = StringField('Submission ID', [validators.Length(max=255)], description="Submission ID (leave blank to create new submission)")



