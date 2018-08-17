
# FlaskForm class definitions for InferenceTool

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class InferenceToolForm(FlaskForm):
    tool_settings_name = StringField('tool_settings_name', [validators.Length(max=255), NonEmpty()])
    tool_name = StringField('tool_name', [validators.Length(max=255), NonEmpty()])
    tool_version = StringField('tool_version', [validators.Length(max=255), NonEmpty()])
    tool_starting_database = TextAreaField('tool_starting_database', [validators.Length(max=10000), NonEmpty()])
    tool_settings = TextAreaField('tool_settings', [validators.Length(max=10000), NonEmpty()])


