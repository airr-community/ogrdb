# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for GermlineSet and associated objects

from sequence_format import check_duplicate

class GermlineSetMixin:
    def delete_dependencies(self, db):
        for a in self.acknowledgements:
            db.session.delete(a)

    def can_see(self, user):
        return(self.status == 'published' or
            user and user.is_authenticated and
               #(user.has_role('Admin') or
                user.has_role(self.species))

    def can_edit(self, user):
        return((user and user.is_authenticated) and
            ((user.has_role('AdminEdit') or
            (user.has_role(self.species) and self.status == 'draft'))))

    def can_draft(self, user):
        return((user and user.is_authenticated) and
            #(user.has_role('Admin') or
             (user.has_role(self.species) and self.status == 'published'))

    def can_see_notes(self, user):
        return((user and user.is_authenticated) and
            #(user.has_role('Admin') or
             user.has_role(self.species))


