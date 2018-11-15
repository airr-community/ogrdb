# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for PrimerSet

class PrimerSetMixin:
    def delete_dependencies(self, db):
        # primers
        for p in self.primers:
            db.session.delete(p)
