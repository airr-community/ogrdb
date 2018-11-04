# Mixin methods for PrimerSet

class PrimerSetMixin:
    def delete_dependencies(self, db):
        # primers
        for p in self.primers:
            db.session.delete(p)
