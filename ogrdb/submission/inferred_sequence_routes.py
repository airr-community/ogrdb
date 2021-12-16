# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import sys

from flask import flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required
from markupsafe import Markup
from wtforms import ValidationError

from head import app, db
from db.inferred_sequence_db import InferredSequence, make_InferredSequence_view, save_InferredSequence, populate_InferredSequence
from ogrdb.submission.inferred_sequence_compound_form import LinkedRecordSet_table, setup_inferred_sequence_form, update_inf_rep_details


@app.route('/inferred_sequence/<id>', methods=['GET'])
def inferred_sequence(id):
    seq = db.session.query(InferredSequence).filter_by(id = id).one_or_none()
    if seq is None:
        flash('Record not found')
        return redirect('/')
    elif not seq.submission.can_see(current_user):
        flash('You do not have rights to view that entry')
        return redirect('/')

    sub = seq.submission
    repo =  sub.repertoire[0].repository_name if sub.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else None

    table = make_InferredSequence_view(seq)
    srr_table = LinkedRecordSet_table(seq.record_set)

    for i in range(len(table.items)-1, -1, -1):
        if table.items[i]['value'] is None or table.items[i]['item'] == 'Extension?' or (table.items[i]['item'] == 'Select sets' and repo):
            del(table.items[i])
        elif table.items[i]['item'] == 'Accession Number' and repo == 'NCBI SRA':
            table.items[i]['value'] = Markup('<a href="https://www.ncbi.nlm.nih.gov/nuccore/%s">%s</a>' % (table.items[i]['value'], table.items[i]['value']))
        elif table.items[i]['item'] == 'Accession Number' and repo == 'ENA':
            table.items[i]['value'] = Markup('<a href="https://www.ebi.ac.uk/ena/data/view/%s">%s</a>' % (table.items[i]['value'], table.items[i]['value']))

    return render_template('inferred_sequence_view.html', table=table, sub_id=sub.submission_id, seq_id=seq.sequence_details.sequence_id, srr_table = srr_table, ncbi=(repo is not None))


def check_inferred_sequence_edit(id):
    try:
        desc = db.session.query(InferredSequence).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None
        elif not desc.submission.can_edit(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc


def validate_ext(c_seq, c_start, c_end):
    if c_seq.data or c_start.data or c_end.data:
        for control in [c_seq, c_start, c_end]:
            if control.data is None:
                control.errors.append('Field cannot be empty.')
                raise ValidationError()
        for control in [c_start, c_end]:
            if int(control.data) < 1 or int(control.data) > 1100:
                control.errors.append('co-ordinate is implausible.')
                raise ValidationError()
        if int(c_start.data) > int(c_end.data):
            c_end.errors.append('End co-ordinate must be greater than or equal to start co-ordinate')
            raise ValidationError()
        if len(c_seq.data) != int(c_end.data) - int(c_start.data) + 1:
            c_seq.errors.append('Co-ordinates do not match sequence length.')
            raise ValidationError()


@app.route('/edit_inferred_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_inferred_sequence(id):
    seq = check_inferred_sequence_edit(id)
    if seq is None:
        return redirect('/')

    if len(seq.submission.genotype_descriptions) < 1:
        flash('Please create at least one Genotype before editing inferred sequences.')
        return redirect(url_for('edit_submission', id=seq.submission.submission_id))

    form = setup_inferred_sequence_form(seq)
    srr_table = LinkedRecordSet_table(seq.record_set)
    repo = seq.submission.repertoire[0].repository_name if seq.submission.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else None

    if repo is None:
        form.seq_record_title.type = 'HiddenField'

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor='inferred_sequence'))

        # Update choices for sequence_id to reflect the selected genotype, provided we have a valid genotype
        # if anything goes wrong, field validation will sort it out

        try:
            for desc in seq.submission.genotype_descriptions:
                if int(form.genotype_id.data) == desc.id:
                    form.sequence_id.choices = [(str(genotype.id), genotype.sequence_id) for genotype in desc.genotypes]
        except:
            pass

        # Clean out the extension fields if we are not using them, so they can't fail validation
        if not form.inferred_extension.data:
            for control in [form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext, form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext]:
                control.data = None

        if form.validate():
            try:
                if form.sequence_id.data == '':
                    form.sequence_id.errors.append('Please select a sequence from the genotype. Upload data to the genotype if no sequences are listed.')
                    raise ValidationError()

                for sequence in seq.submission.inferred_sequences:
                    if sequence is not seq and str(sequence.sequence_id) == form.sequence_id.data and str(sequence.genotype_id) == form.genotype_id.data:
                        form.sequence_id.errors.append('That inferred sequence is already listed in the submission.')
                        raise ValidationError()

                if form.inferred_extension.data:
                    validate_ext(form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext)
                    validate_ext(form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext)
                    if not(form.ext_3prime.data or form.ext_5prime.data):
                        form.inferred_extension.errors.append('Please specify an extension at at least one end')
                        raise ValidationError()

                update_inf_rep_details(seq, form, repo)
                save_InferredSequence(db, seq, form, new=False)
                srr_table = LinkedRecordSet_table(seq.record_set)

                if 'save_close_sequence' in request.form:
                    return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor= 'inferred_sequence'))
            except ValidationError as e:
                return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id, ncbi=repo is not None, srr_table=srr_table)
    else:
        populate_InferredSequence(db, seq, form)
        form.genotype_id.data = str(seq.genotype_id) if seq.genotype_id else ''
        form.sequence_id.data = str(seq.sequence_id) if seq.sequence_id else ''

    return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id, ncbi=repo is not None, srr_table=srr_table)