
# FlaskForm class definitions for InferenceTool

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class InferenceToolForm(FlaskForm):
    tool_settings_name = StringField('Tool/Settings Name', [validators.Length(max=255), NonEmpty()], description="Descriptive name for this combination of tool and settings")
    tool_name = StringField('Tool Name', [validators.Length(max=255), NonEmpty()], description="Name of the inference tool")
    tool_version = StringField('Tool Version', [validators.Length(max=255), NonEmpty()], description="Version of the inference tool")
    tool_starting_database = TextAreaField('Starting Database', [validators.Length(max=10000), NonEmpty()], description="Starting germline database used by the tool (please specify where and when it was obtained, name, and version id, if any)")
    tool_settings = TextAreaField('Settings', [validators.Length(max=10000), NonEmpty()], description="Settings/configuration of the tool when used to provide the inferences")


