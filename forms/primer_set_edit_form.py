# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Composite tables for Edit Primer Set page - defined manually

from db.editable_table import *
from db.primer_db import *
from db.primer_set_db import *
from forms.aggregate_form import AggregateForm
from forms.primer_form import *
from forms.primer_set_form import *


class EditablePrimerTable(EditableTable):
    def check_add_item(self, request, db):
        added = False
        if self.form.add_primers.data:
            try:
                if len(self.form.primer_name.data) < 1:
                    self.form.primer_name.errors = ['Name cannot be blank.']
                    raise ValueError()
                if self.form.primer_name.data in [i.primer_name for i in self.items]:
                    self.form.primer_name.errors = ['A primer with that name is already in the table']
                    raise ValueError()
                if len(self.form.primer_seq.data) < 1:
                    self.form.primer_seq.errors = ['Sequence cannot be blank.']
                    raise ValueError()
                else:
                    v = ValidNucleotideSequence(ambiguous = True)
                    try:
                        v.__call__(self.form, self.form.primer_seq)
                    except ValidationError:
                        self.form.primer_seq.errors = ['Invalid sequence.']
                        raise ValueError()

                p = Primer()
                p.primer_name = self.form.primer_name.data
                p.primer_seq = self.form.primer_seq.data
                self.items.append(p)
                self.table = make_Primer_table(self.items)
                db.session.commit()
                added = True
            except ValueError as e:
                pass

        return (added, None, None)


def setup_primer_set_forms_and_tables(db, set):
    tables = {}
    tables['primers'] = EditablePrimerTable(make_Primer_table(set.primers), 'primers', PrimerForm, set.primers, legend='Add Primer')

    form = tables['primers'].form
    return (form, tables)
