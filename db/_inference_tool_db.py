# Mixin methods for InferenceTool

class InferenceToolMixin:
    def delete_dependencies(self, db):
        # genotype descriptions
        for d in self.genotype_descriptions:
            d.delete_dependencies(db)
            db.session.delete(d)
