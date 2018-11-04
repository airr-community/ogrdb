# Mixin methods for Repertoire and associated objects

class RepertoireMixin:
    def delete_dependencies(self, db):
        # inference tools and everything downstream
        for t in self.submission.inference_tools:
            t.delete_dependencies(db)
            db.session.delete(t)

        # publications
        for p in self.pub_ids:
            db.session.delete(p)

        # primers
        for s in self.primer_sets:
            s.delete_dependencies(db)
            db.session.delete(s)
