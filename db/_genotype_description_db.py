# Mixin methods for Genotype

class GenotypeDescriptionMixin:
    def delete_dependencies(self, db):
        # genotype records
        for g in self.genotypes:
            db.session.delete(g)
        # inferred sequences
        for s in self.inferred_sequences:
            db.session.delete(s)