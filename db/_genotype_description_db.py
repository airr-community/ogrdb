# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for Genotype

class GenotypeDescriptionMixin:
    def delete_dependencies(self, db):
        # genotype records
        for g in self.genotypes:
            db.session.delete(g)
        # sample ids
        for s in self.sample_names:
            db.session.delete(s)
        #record sets
        for r in self.record_set:
            db.session.delete(r)
