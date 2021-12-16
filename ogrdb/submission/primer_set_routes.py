# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import io
import sys
from Bio import SeqIO

from flask import flash, redirect, request, render_template, url_for
from flask_login import current_user, login_required

from head import db, app
from db.primer_db import Primer
from db.primer_set_db import PrimerSet, populate_PrimerSet
from forms.primer_set_form import PrimerSetForm
from ogrdb.submission.submission_edit_form import process_table_updates
from ogrdb.submission.primer_set_edit_form import setup_primer_set_forms_and_tables


def check_primer_set_edit(id):
    try:
        set = db.session.query(PrimerSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return (None, None)

        sub = set.repertoire.submission
        if not sub.can_edit(current_user):
            flash('You do not have rights to edit that primer set.')

        return (sub, set)

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return (None, None)


@app.route('/primer_sets/<id>', methods=['GET', 'POST'])
@login_required
def primer_sets(id):
    (sub, set) = check_primer_set_edit(id)
    if set is None:
        return redirect('/submissions')

    form = PrimerSetForm()

    if request.method == 'GET':
        populate_PrimerSet(db, set, form)
        return render_template('primer_set_edit.html', form=form, name=set.primer_set_name, id=id)
    else:
        if 'cancel_btn' in request.form:
            if len(set.primer_set_name) == 0:         # this is a new primer set, since you can't save a blank name
                db.session.delete(set)
                db.session.commit()
            return redirect(url_for('edit_submission', id=sub.submission_id, _anchor='primer_sets'))

        valid = form.validate()

        if valid:
            set.primer_set_name = form.primer_set_name.data
            set.primer_set_notes = form.primer_set_notes.data
            db.session.commit()

            if 'edit_btn' in request.form:
                return redirect(url_for('edit_primers', id=id, _anchor='primer_sets'))
            elif 'submit_btn' in request.form:
                return redirect(url_for('edit_submission', id=sub.submission_id, _anchor='primer_sets'))

        return render_template('primer_set_edit.html', form=form, name=set.primer_set_name, id=id)


@app.route('/edit_primers/<id>', methods=['GET', 'POST'])
@login_required
def edit_primers(id):
    (sub, set) = check_primer_set_edit(id)
    if set is None:
        return redirect('/submissions')

    (form, tables) = setup_primer_set_forms_and_tables(db, set)

    if request.method == 'GET':
        return render_template('primers_edit.html', tables=tables, form=form, name=set.primer_set_name, id=id)
    else:
        if 'close_btn' in request.form:
            return redirect(url_for('primer_sets', id=id))

        valid = form.validate()

        if valid:
            validation_result = process_table_updates({'primers': tables['primers']}, request, db)
            if validation_result.tag:
                if validation_result.valid:     # rebuild tables if something has changed
                    (form, tables) = setup_primer_set_forms_and_tables(db, set)

        return render_template('primers_edit.html', tables=tables, form=form, name=set.primer_set_name, id=id)


@app.route('/upload_primers/<id>', methods=['POST'])
@login_required
def upload_primer(id):
    (sub, set) = check_primer_set_edit(id)
    if set is None:
        return redirect('/submissions')

    if 'file' not in request.files:
        flash('Nothing uploaded.')
    else:
        content = io.StringIO(request.files['file'].read().decode("utf-8"))
        seq_count = 0

        for seq_record in SeqIO.parse(content, 'fasta'):
            seq_count += 1

            p = Primer()
            p.primer_name = seq_record.id
            p.primer_seq = str(seq_record.seq)
            db.session.add(p)
            set.primers.append(p)

        if seq_count > 0:
            flash('Added %d primer records' % seq_count)
            db.session.commit()
        else:
            flash('No valid FASTA records found in file.')

    return ''