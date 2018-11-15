# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for InferenceTool

class InferenceToolMixin:
    def delete_dependencies(self, db):
        # genotype descriptions
        for d in self.genotype_descriptions:
            d.delete_dependencies(db)
            db.session.delete(d)
