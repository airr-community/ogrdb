# FlaskForm class definitions for Repertoire

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField
class RepertoireForm(FlaskForm):
    repository_name = StringField('repository_name')
    repository_id = StringField('repository_id')
    dataset_url = StringField('dataset_url')
    dataset_doi = StringField('dataset_doi')
    miarr_compliant = BooleanField('miarr_compliant')
    miairr_link = StringField('miairr_link')
    sequencing_platform = StringField('sequencing_platform')
    read_length = StringField('read_length')
    primers_not_overlapping = BooleanField('primers_not_overlapping')
    notes = StringField('notes')


