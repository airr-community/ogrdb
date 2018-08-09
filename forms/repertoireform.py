
# FlaskForm class definitions for PubId

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, validators
class PubIdForm(FlaskForm):
    pubmed_id = IntegerField('pubmed_id', [validators.Optional()])



# FlaskForm class definitions for ForwardPrimer

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, validators
class ForwardPrimerForm(FlaskForm):
    fw_primer_name = StringField('fw_primer_name')
    fw_primer_seq = StringField('fw_primer_seq', [ValidNucleotideSequence(ambiguous=True)])



# FlaskForm class definitions for ReversePrimer

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, validators
class ReversePrimerForm(FlaskForm):
    rv_primer_name = StringField('rv_primer_name')
    rv_primer_seq = StringField('rv_primer_seq', [ValidNucleotideSequence(ambiguous=True)])



# FlaskForm class definitions for Acknowledgements

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, validators
class AcknowledgementsForm(FlaskForm):
    ack_name = StringField('ack_name')
    ack_institution_name = StringField('ack_institution_name')
    ack_ORCID_id = StringField('ack_ORCID_id', [validators.Optional(), ValidOrcidID()])



# FlaskForm class definitions for Repertoire

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, validators
class RepertoireForm(FlaskForm):
    repository_name = StringField('repository_name')
    repository_id = StringField('repository_id')
    dataset_url = StringField('dataset_url')
    dataset_doi = StringField('dataset_doi')
    miarr_compliant = SelectField('miarr_compliant', choices=[(True, True), (False, False)])
    miairr_link = StringField('miairr_link')
    sequencing_platform = StringField('sequencing_platform')
    read_length = StringField('read_length')
    primers_not_overlapping = SelectField('primers_not_overlapping', choices=[(True, True), (False, False)])


