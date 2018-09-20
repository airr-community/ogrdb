# Mixin methods for Submission and associated objects

class SubmissionMixin:
    def delete_dependencies(self, db):
        # repertoire and everything downstream
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

