# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import sys
from os import mkdir
from os.path import isdir
from traceback import format_exc

from flask import flash, redirect, url_for, request, render_template
from wtforms import ValidationError

from head import app, db, attach_path
from flask_login import login_required, current_user

from db.misc_db import Committee
from db.genotype_description_db import GenotypeDescription, save_GenotypeDescription, populate_GenotypeDescription
from ogrdb.submission.genotype_description_compound_form import setup_genotype_description_form, LinkedSample_table, \
    update_sample_details
from ogrdb.submission.genotype_upload import file_to_genotype
from ogrdb.submission.inferred_sequence_compound_form import LinkedRecordSet_table


def check_genotype_description_edit(id):
    try:
        desc = db.session.query(GenotypeDescription).filter_by(id = id).one_or_none()
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


@app.route('/edit_genotype_description/<id>', methods=['GET', 'POST'])
@login_required
def edit_genotype_description(id):
    desc = check_genotype_description_edit(id)
    if desc is None:
        return redirect('/')

    if len(desc.submission.inference_tools) < 1:
        flash('Please create at least one Inference Tool entry before editing a Genotype.')
        return redirect(url_for('edit_submission', id=desc.submission.submission_id))

    form = setup_genotype_description_form(desc)
    form.locus.choices = [(x,x) for x in db.session.query(Committee).filter(Committee.species==desc.submission.species).one_or_none().loci.replace(' ', '').split(',')]
    form.sequence_type.choices = [(x,x) for x in db.session.query(Committee).filter(Committee.species==desc.submission.species).one_or_none().sequence_types.replace(' ', '').split(',')]
    sam_table = LinkedSample_table(desc.sample_names)
    srr_table = LinkedRecordSet_table(desc.record_set)
    repo = desc.submission.repertoire[0].repository_name if desc.submission.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else None

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))

        if form.validate():
            try:
                if form.genotype_name.data != desc.genotype_name and form.genotype_name.data in [d.genotype_name for d in desc.submission.genotype_descriptions]:
                    form.genotype_name.errors.append('There is already a genotype description with that name.')
                    raise ValidationError()

                update_sample_details(desc, form, repo)
                sam_table = LinkedSample_table(desc.sample_names)
                srr_table = LinkedRecordSet_table(desc.record_set)

                if form.genotype_file.data:
                    form.genotype_filename.data = form.genotype_file.data.filename
                    save_GenotypeDescription(db, desc, form, new=False)

                    dirname = attach_path + desc.submission.submission_id

                    try:
                        if not isdir(dirname):
                            mkdir(dirname)
                        with open(dirname + '/genotype_%s.csv' % desc.id, 'w', newline='') as fo:
                            fo.write(form.genotype_file.data.read().decode("utf-8"))
                    except:
                        info = sys.exc_info()
                        flash('Error saving genotype file: %s' % (info[1]))
                        app.logger.error(format_exc())
                        return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)

                    for g in desc.genotypes:
                        db.session.delete(g)
                    db.session.commit()
                    file_to_genotype(dirname + '/genotype_%s.csv' % desc.id, desc, db)
                else:
                    form.genotype_filename.data = desc.genotype_filename       # doesn't get passed back in request as the field is read-only
                    save_GenotypeDescription(db, desc, form, new=False)

                if 'save_close_genotype' in request.form:
                    return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))
            except ValidationError as e:
                return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id, ncbi=(repo is not None), sam_table=sam_table, srr_table=srr_table)
    else:
        populate_GenotypeDescription(db, desc, form)
        if desc.inference_tool is not None:
            form.inference_tool_id.data = str(desc.inference_tool_id)
            form.inference_tool_id.default = str(desc.inference_tool_id)

    return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id, ncbi=(repo is not None), sam_table=sam_table, srr_table=srr_table)


def check_genotype_description_view(id):
    try:
        desc = db.session.query(GenotypeDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None
        elif not desc.submission.can_see(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc
