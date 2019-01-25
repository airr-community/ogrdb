# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for Submission and associated objects

from shutil import rmtree
from sys import exc_info
from app import app
from traceback import format_exc

class SubmissionMixin:
    def delete_dependencies(self, db):
        # repertoire and everything downstream
        for i in self.inferred_sequences:
            i.delete_dependencies(db)
            db.session.delete(i)

        for d in self.genotype_descriptions:
            d.delete_dependencies(db)
            db.session.delete(d)

        for r in self.repertoire:
            r.delete_dependencies(db)
            db.session.delete(r)

        for n in self.notes_entries:
            db.session.delete(n)

        # acknowledgements
        for a in self.acknowledgements:
            db.session.delete(a)

        # journal entries
        for j in self.journal_entries:
            db.session.delete(j)


        # associated files
        try:
            rmtree('attachments/' + self.submission_id)
        except:
            app.logger.error(format_exc())


    def can_see(self, user):
        return(self.public or
            user.is_authenticated and
               #(user.has_role('Admin') or
                user.has_role(self.species) or \
                self.owner == user) or \
                user in self.delegates

    def can_edit(self, user):
        return(user.is_authenticated and
                #(user.has_role('Admin') or
                 (self.owner == user and self.submission_status == 'draft'))

    def can_see_private(self, user):
        return(user.is_authenticated and
                (self.owner == user or user.has_role(self.species) or user in self.delegates))