
# FlaskForm class definitions for PubId

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class PubIdForm(FlaskForm):
    pubmed_id = StringField('pubmed_id', [validators.Length(max=255)])



# FlaskForm class definitions for ForwardPrimer

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class ForwardPrimerForm(FlaskForm):
    fw_primer_name = TextAreaField('fw_primer_name', [validators.Length(max=10000)])
    fw_primer_seq = StringField('fw_primer_seq', [ValidNucleotideSequence(ambiguous=True)])



# FlaskForm class definitions for ReversePrimer

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class ReversePrimerForm(FlaskForm):
    rv_primer_name = TextAreaField('rv_primer_name', [validators.Length(max=10000)])
    rv_primer_seq = StringField('rv_primer_seq', [ValidNucleotideSequence(ambiguous=True)])



# FlaskForm class definitions for Acknowledgements

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class AcknowledgementsForm(FlaskForm):
    ack_name = TextAreaField('ack_name', [validators.Length(max=10000)])
    ack_institution_name = StringField('ack_institution_name', [validators.Length(max=255)])
    ack_ORCID_id = StringField('ack_ORCID_id', [validators.Optional(), ValidOrcidID()])



# FlaskForm class definitions for Repertoire

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class RepertoireForm(FlaskForm):
    repository_name = StringField('repository_name', [validators.Length(max=255)])
    repository_id = StringField('repository_id', [validators.Length(max=255)])
    dataset_url = StringField('dataset_url', [validators.Length(max=255)])
    dataset_doi = StringField('dataset_doi', [validators.Length(max=255)])
    miarr_compliant = SelectField('miarr_compliant', choices=[('Yes', 'Yes'), ('No', 'No')])
    miairr_link = StringField('miairr_link', [validators.Length(max=255)])
    sequencing_platform = StringField('sequencing_platform', [validators.Length(max=255)])
    read_length = StringField('read_length', [validators.Length(max=255)])
    primers_overlapping = SelectField('primers_overlapping', choices=[('Yes', 'Yes'), ('No', 'No')])


