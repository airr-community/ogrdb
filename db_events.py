# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Event handlers for database changes

from sqlalchemy import event
from db.gene_description_db import *
from db.inferred_sequence_db import *
from db.submission_db import *
from db.submission_db import *

from head import db

# Keep the duplicate sequences/published duplicates mapping up-to-date

# At the GeneDescription end, the mapping changes if the defined sequence is changed.

@event.listens_for(GeneDescription.sequence, 'set')
def receive_gd_set(target, value, oldvalue, initiator):
    print('GeneDescription Set event fired')
    target.build_duplicate_list(db, value)

# At the Submission end, the mapping gets rebuilt when the submission status changes
# The mapping is always null when the submission is in draft, and this is the only point that the sequences can be changed

@event.listens_for(Submission.submission_status, 'set')
def receive_gd_set(target, value, oldvalue, initiator):
    print('Submission Set event fired')
    for gd in target.genotype_descriptions:
        for genotype in gd.genotypes:
            genotype.build_duplicate_list(db, value)
