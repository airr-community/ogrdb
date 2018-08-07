# Composite form for Edit Submission page - defined manually

from flask_wtf import FlaskForm

class SubEditForm(FlaskForm):
    def __init__(self, submission_form, repertoire_form, pubmed_form):
        self.submission_form = submission_form
        self.repertoire_form = repertoire_form
        self.pubmed_form = pubmed_form

    def __getattr__(self, attr):
        for obj in (self.submission_form, self.repertoire_form, self.pubmed_form):
            a = getattr(obj, attr, None)
            if a is not None: return a
        raise(AttributeError())

