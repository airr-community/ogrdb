# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import SelectField, SubmitField, StringField, IntegerField, BooleanField


class NewSequenceForm(FlaskForm):
    new_name = StringField('New Sequence Name', description="The name for this new sequence")
    species_subgroup = StringField('Species Subgroup', description="Species subgroup for this new sequence, if any")
    submission_id = SelectField('Submission ID', description="Inference study on which this new sequence is based")
    sequence_name = SelectField('Sequence', description="Inferred sequence on which this new sequence is based")
    upload_file = FileField('Sequence File', description="CSV file containing sequence metadata")
    merge_data = BooleanField('Merge Data', description="Merge custom data (requires specific code support in sequence_routes.custom_merge)")
    gapped_cdr1_start = IntegerField('Gapped CDR1 Start', description="CDR1 start co-ordinate in the gapped alignment (V-genes only)")
    gapped_cdr1_end = IntegerField('Gapped CDR1 End', description="CDR1 end co-ordinate in the gapped alignment (V-genes only)")
    gapped_cdr2_start = IntegerField('Gapped CDR2 Start', description="CDR2 start co-ordinate in the gapped alignment (V-genes only)")
    gapped_cdr2_end = IntegerField('Gapped CDR2 End', description="CDR2 end co-ordinate in the gapped alignment (V-genes only)")
    gapped_cdr3_start = IntegerField('Gapped CDR3 Start', description="CDR3 start co-ordinate in the gapped alignment (V-genes only)")
    evidence_file = FileField('Evidence File', description="CSV file containing sequence metadata")
    create = SubmitField('Create')
    cancel = SubmitField('Cancel')
