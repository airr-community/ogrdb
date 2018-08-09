# Composite form for Edit Submission page - defined manually

from flask import flash
from wtforms import SubmitField, IntegerField
from copy import deepcopy
from db.repertoiredb import *
from db.submissiondb import *
from db.miscdb import *
from forms.repertoireform import *
from forms.submissionform import *

class AggregateForm(FlaskForm):
    def __init__(self, *args):
        super().__init__()
        self.subforms = []

        for form in args:
            self.subforms.append(form)
            self._fields.update(form._fields)

    def __getattr__(self, attr):
        for form in self.subforms:
            a = getattr(form, attr, None)
            if a is not None: return a
        raise(AttributeError())

# Helper functions for the route

class DelCol(Col):
    def __init__(self, name):
        super().__init__('')
        self.name = name
    def td_format(self, content):
        return '<button id="%s_del_%s" name="%s_del_%s" type="submit" value="Del" class="btn btn-xs btn-danger"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>'  % (self.name, content, self.name, content)


def prep_for_edit_form(sub, table, name, form, legend, ids):
    # Build as much as we can dynamically, to avoid the need for extraneous files
    # use a deepcopy of the class to avoid permanently modifying its members
    # we still need a jinja template for each table, though
    dynform = deepcopy(form)
    # Add the dynamic controls to the deepcopy
    setattr(dynform, 'add_%s' % (name), SubmitField(legend))
    for pmid in ids:
        setattr(dynform, '%s_del_%d' % (name, pmid.id), SubmitField('Del'))
    form = dynform()

    # Subclass the table to provide refs to the delete buttons on each row
    table.add_column('id', DelCol(name))
    return (table, form)

def setup_sub_forms_and_tables(sub, db):
    tables = {}

    if len(sub.repertoire) == 0:
        sub.repertoire.append(Repertoire())
        db.session.commit()

    submission_form = SubmissionForm(obj = sub)
    species = db.session.query(Committee.species).all()
    submission_form.species.choices = [(s[0],s[0]) for s in species]

    repertoire_form = RepertoireForm(obj = sub.repertoire)

    (tables['pubmed_table'], pubmed_form) = prep_for_edit_form(sub, make_PubId_table(sub.repertoire[0].pub_ids, classes=['table table-bordered']), 'pubmed', PubIdForm, 'Add Publication', sub.repertoire[0].pub_ids)
    (tables['fw_primer'], fw_primer_form) = prep_for_edit_form(sub, make_ForwardPrimer_table(sub.repertoire[0].forward_primer_set, classes=['table table-bordered']), 'fw_primer', ForwardPrimerForm, 'Add Primer', sub.repertoire[0].forward_primer_set)
    (tables['rv_primer'], rv_primer_form) = prep_for_edit_form(sub, make_ReversePrimer_table(sub.repertoire[0].reverse_primer_set, classes=['table table-bordered']), 'rv_primer', ReversePrimerForm, 'Add Primer', sub.repertoire[0].reverse_primer_set)
    (tables['ack'], ack_form) = prep_for_edit_form(sub, make_Acknowledgements_table(sub.acknowledgements, classes=['table table-bordered']), 'ack', AcknowledgementsForm, 'Add Acknowledgement', sub.acknowledgements)

    form = AggregateForm(submission_form, repertoire_form, pubmed_form, fw_primer_form, rv_primer_form, ack_form)
    return (tables, form)




