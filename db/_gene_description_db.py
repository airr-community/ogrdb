# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for Submission and associated objects

from db.journal_entry_db import JournalEntry
from sqlalchemy import inspect

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
            #(user.has_role('Admin') or
             (user.has_role(self.organism) and self.status == 'draft'))

    def can_draft(self, user):
        return(user.is_authenticated and
            #(user.has_role('Admin') or
             (user.has_role(self.organism) and self.status == 'published'))

