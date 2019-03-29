# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for Submission and associated objects

from db.journal_entry_db import JournalEntry
from sqlalchemy import inspect
from db.submission_db import *

class GeneDescriptionMixin:
    def delete_dependencies(self, db):
        for a in self.acknowledgements:
            db.session.delete(a)

    def can_see(self, user):
        return(self.status == 'published' or
            user.is_authenticated and
               #(user.has_role('Admin') or
                user.has_role(self.organism))

    def can_edit(self, user):
        return(user.is_authenticated and
            ((user.has_role('Admin') or
            (user.has_role(self.organism) and self.status == 'draft'))))

    def can_draft(self, user):
        return(user.is_authenticated and
            #(user.has_role('Admin') or
             (user.has_role(self.organism) and self.status == 'published'))

    # Find any submitted inferences out there that refer to this sequence

    def build_duplicate_list(self, db, new_seq):
        # new_seq is the sequence about to be added to the gene description
        self.duplicate_sequences = list()
        subs = db.session.query(Submission).filter(Submission.submission_status.in_(['reviewing', 'complete']), Submission.species == self.organism).all()

        for sub in subs:
            for inf in sub.inferred_sequences:
                try:
                    inf_seq = inf.sequence_details.nt_sequence
                    if len(inf_seq) > 0 and len(new_seq) > 0:
                        if(inf_seq in new_seq or new_seq in inf_seq):
                            self.duplicate_sequences.append(inf)
                except:
                    continue

        db.session.commit()

