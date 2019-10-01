# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for Submission and associated objects

from db.submission_db import *
from sequence_format import check_duplicate

class GeneDescriptionMixin:
    def delete_dependencies(self, db):
        for a in self.acknowledgements:
            db.session.delete(a)
        for d in self.dupe_notes:
            db.session.delete(d)

    def can_see(self, user):
        return(self.status == 'published' or
            user.is_authenticated and
               #(user.has_role('Admin') or
                user.has_role(self.organism))

    def can_edit(self, user):
        return(user.is_authenticated and
            ((user.has_role('AdminEdit') or
            (user.has_role(self.organism) and self.status == 'draft'))))

    def can_draft(self, user):
        return(user.is_authenticated and
            #(user.has_role('Admin') or
             (user.has_role(self.organism) and self.status == 'published'))

    def can_see_notes(self, user):
        return(user.is_authenticated and
            #(user.has_role('Admin') or
             user.has_role(self.organism))

    # Find any submitted inferences out there that refer to this sequence

    def build_duplicate_list(self, db, new_seq):
        self.duplicate_sequences = list()

        if new_seq is not None:
            # new_seq is the sequence about to be added to the gene description
            new_seq = new_seq.replace('.', '')      # ignore leading or trailing dots
            subs = db.session.query(Submission).filter(Submission.submission_status.in_(['reviewing', 'complete']), Submission.species == self.organism).all()

            for sub in subs:
                for desc in sub.genotype_descriptions:
                    if desc.sequence_type == self.sequence_type:
                        for genotype in desc.genotypes:
                            if check_duplicate(genotype.nt_sequence, new_seq, self.sequence_type):
                                self.duplicate_sequences.append(genotype)

            db.session.commit()

