# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import datetime
from os import mkdir, remove
from os.path import isdir
from traceback import format_exc

from flask import request, render_template, redirect, flash, Response
from flask_login import current_user, login_required

from db.journal_entry_db import JournalEntry
from db.submission_db import Submission, save_Submission, populate_Submission
from head import app, attach_path
from journal import add_history, add_note
from mail import send_mail
from textile_filter import safe_textile

from ogrdb.submission.submission_edit_form import *
from ogrdb.submission.submission_list_table import setup_submission_list_table
from ogrdb.submission.submission_view_form import setup_submission_view_forms_and_tables


@app.route('/submissions', methods=['GET', 'POST'])
def submissions():
    tables = {}
    show_completed = False

    if current_user.is_authenticated:
        q = db.session.query(Submission).join(Submission.owner).filter(User.email==current_user.email)
        results = q.all()
        tables['mine'] = setup_submission_list_table(results, current_user)
        tables['mine'].table_id = 'mine'

        delegated_species = {}
        for sub in current_user.delegated_submissions:
            delegated_species[sub.species] = True

        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp) or sp in delegated_species:
                if 'completed' in request.args and request.args['completed'] == 'yes':
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing', 'complete', 'withdrawn']))
                    show_completed = True
                else:
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing']))
                    show_completed = False
                results = q.all()

                if 'species' not in tables:
                    tables['species'] = {}
                tables['species'][sp] = setup_submission_list_table(results, current_user)
                tables['species'][sp].table_id = sp

    q = db.session.query(Submission).filter_by(public=1)
    results = q.all()
    tables['public'] = setup_submission_list_table(results, current_user)
    tables['public'].table_id = 'public'

    return render_template('submission_list.html', tables=tables, show_completed=show_completed)


@app.route('/new_submission', methods=['GET', 'POST'])
@login_required
def new_submission():
    form = SubmissionForm()
    species = db.session.query(Committee.species).all()
    form.species.choices = [(s[0],s[0]) for s in species]
    form.submission_status.data = 'draft'
    form.submission_date.data = datetime.date.today()
    form.population_ethnicity.data = 'UN'
    form.submitter_email.data = current_user.email
    form.submitter_name.data = current_user.name
    form.submitter_address.data = current_user.address

    if request.method == 'POST':
        if form.validate():
            sub = Submission()
            sub.owner = current_user
            sub.submission_status = 'draft'
            save_Submission(db, sub, form, True)
            sub.submission_id = "S%05d" % sub.id
            db.session.commit()
            return redirect(url_for('edit_submission', id=sub.submission_id))

    return render_template('submission_new.html', form=form, url='new_submission')


def check_sub_edit(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None:
        flash('Submission not found')
        return None
    elif not sub.can_edit(current_user):
        flash('You do not have rights to edit that submission')
        return None
    return sub


def check_sub_view(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None:
        flash('Submission not found')
        return None
    elif not sub.can_see(current_user):
        flash('You do not have rights to view that submission')
        return None
    return sub


def check_sub_attachment_edit(id):
    af = db.session.query(AttachedFile).filter_by(i =id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    sub = af.notes_entry.submission
    if not sub.can_edit(current_user):
        flash('You do not have rights to delete that attachment')
        return None
    return af


def check_sub_attachment_view(id):
    af = db.session.query(AttachedFile).filter_by(id = id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    sub = af.notes_entry.submission
    if not sub.can_see(current_user):
        flash('You do not have rights to download that attachment')
        return None
    return af


@app.route('/edit_submission/<id>', methods=['GET', 'POST'])
@login_required
def edit_submission(id):
    sub = check_sub_edit(id)
    if sub is None:
        return redirect('/submissions')

    (tables, form) = setup_submission_edit_forms_and_tables(sub, db)

    if request.method == 'GET':
        populate_Submission(db, sub, form)
        populate_Repertoire(db, sub.repertoire[0], form)
        form.repository_select.data = sub.repertoire[0].repository_name if sub.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else 'Other'
        return render_template('submission_edit.html', form=form, id=id, tables=tables, attachment=len(sub.notes_entries[0].attached_files) > 0)

    validation_result = ValidationResult()
    try:
        if 'save_btn' in request.form or 'save_close_btn' or 'submit_btn' in request.form:
            if not form.validate():
                if 'submit_btn' in request.form:
                    raise ValidationError()

                # Overlook empty field errors when saving to draft
                nonblank_errors = False
                for field in form._fields:
                    if len(form._fields[field].errors) > 0:
                        if len(form._fields[field].data) == 0:
                            form._fields[field].errors = []
                        else:
                            nonblank_errors = True
                if nonblank_errors:
                    raise ValidationError()

        # Check if this is an NCBI related repertoire, and, if so, validate accession number and update related fields

        choice = form.repository_select.data
        update_sra_rep_details(form)

        # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
        validation_result = process_table_updates(tables, request, db)
        if not validation_result.valid:
            raise ValidationError()

        if 'submit_btn' in request.form:
            check_submission_complete(sub, validation_result)

            sub.submission_status = 'reviewing'
            add_history(current_user, 'Submission submitted to IARC %s Committee for review' % sub.species, sub, db)
            send_mail('Submission %s submitted to IARC %s Committee for review' % (sub.submission_id, sub.species), [current_user.email], 'user_submission_submitted', user=current_user, submission=sub)
            send_mail('Submission %s submitted to IARC %s Committee for review' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_received', user=current_user, submission=sub)
            db.session.commit()
            flash('Submission %s has been submitted to IARC for review.' % id)
            return redirect(url_for('submissions'))

        # We've gone too far off-piste to use form initialisation or process() to push field values into the object
        # The main problem is that not all object attributes are represented in the form, for example submission_id
        # if these were present as hidden fields, maybe we could use process()

        if ('save_btn' in request.form or 'save_close_btn' or 'submit_btn' in request.form or 'upload_btn' in request.form):
            for (k, v) in request.form.items():
                if hasattr(sub, k):
                    setattr(sub, k, v)
                elif hasattr(sub.repertoire[0], k):
                    setattr(sub.repertoire[0], k, v)

            # update fields that may have been fetched from NCBI

            sub.repertoire[0].repository_name = form.repository_name.data
            sub.repertoire[0].dataset_url = form.dataset_url.data
            sub.repertoire[0].rep_title = form.rep_title.data

            db.session.commit()

            if 'notes_attachment' in request.files:
                for file in form.notes_attachment.data:
                    if file.filename != '':
                        af = None
                        for at in sub.notes_entries[0].attached_files:
                            if at.filename == file.filename:
                                af = at
                                break
                        if af is None:
                            af = AttachedFile()
                        af.notes_entry = sub.notes_entries[0]
                        af.filename = file.filename
                        db.session.add(af)
                        db.session.commit()
                        dirname = attach_path + sub.submission_id

                        try:
                            if not isdir(dirname):
                                mkdir(dirname)
                            with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                                fo.write(file.stream.read())
                        except:
                            info = sys.exc_info()
                            flash('Error saving attachment: %s' % (info[1]))
                            app.logger.error(format_exc())
                            return redirect(url_for('edit_submission', id=sub.submission_id))

            if 'notes_text' in request.form:
                sub.notes_entries[0].notes_text = request.form['notes_text'].encode('utf-8')

            db.session.commit()
            form.repository_select.data = sub.repertoire[0].repository_name if sub.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else 'Other'

        if validation_result.route:
            return redirect(url_for(validation_result.route, id = validation_result.id))
        if validation_result.tag:
            return redirect(url_for('edit_submission', id=id, _anchor=validation_result.tag))

        if 'save_btn' in request.form or 'upload_btn' in request.form:
            tag = request.form['current_tab'].split('#')[1] if '#' in request.form['current_tab'] else '#sub'
            return redirect(url_for('edit_submission', id=id, _anchor=tag))
        else:
            return redirect(url_for('submissions'))

    except ValidationError as e:
        # If we don't have a tag, find an error to jump to
        if not validation_result.tag:
            repform = type(RepertoireForm())
            for subform in form.subforms:
                if type(subform) is repform:
                    for field in subform:
                        if len(field.errors) > 0:
                            validation_result.tag = 'rep'
                            break
                    break

        if not validation_result.tag:
            for table in tables.values():
                for field in table.form:
                    if len(field.errors) > 0:
                        validation_result.tag = table.name
                        break

        return render_template('submission_edit.html', form=form, id=id, tables=tables, jump=validation_result.tag)


# Check required components of submission are present (particularly this is aimed
# at submissions created automatically from VDJbase

def check_submission_complete(sub, validation_result):
    incomplete = []

    # At least one inferred sequence
    if not sub.inferred_sequences:
        incomplete.append('Submission must contain at least one inferred sequence')
        validation_result.tag = 'inferred_sequence'

    # Genotype records contain sample_ids and sequence sets
    if not sub.genotype_descriptions:
        incomplete.append('Submission must contain at least one inferred genotype')
        validation_result.tag = 'genotype_description'

    for gd in sub.genotype_descriptions:
        if not gd.genotype_biosample_ids:
            incomplete.append('Each genotype must specify the biosample ids')
            validation_result.tag = 'genotype_description'
            break

    for gd in sub.genotype_descriptions:
        if not gd.genotype_run_ids:
            incomplete.append('Each genotype must specify the run ids')
            validation_result.tag = 'genotype_description'
            break

    # At least one primer record

    if not sub.repertoire[0].primer_sets:
        incomplete.append('Submission must contain at least one set of primers')
        validation_result.tag = 'primer_sets'

    if incomplete:
        flash(Markup('<br>'.join(incomplete)))
        raise ValidationError()

    return


@app.route('/download_submission_attachment/<id>')
def download_submission_attachment(id):
    att = check_sub_attachment_view(id)
    if att is None:
        return redirect('/')

    sub = att.notes_entry.submission

    try:
        dirname = attach_path + sub.submission_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_submission_attachment/<id>', methods=['POST'])
def delete_submission_attachment(id):
    att = check_sub_attachment_edit(id)
    if att is None:
        return redirect('/')

    sub = att.notes_entry.submission

    try:
        dirname = attach_path + sub.submission_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


@app.route('/delete_submission/<id>', methods=['GET', 'POST'])
@login_required
def delete_submission(id):
    sub = check_sub_edit(id)
    if sub is not None:
        repo = sub.repertoire[0].repository_name if sub.repertoire[0] else ''
        acc = sub.repertoire[0].rep_accession_no if sub.repertoire[0] else ''
        app.logger.info('User %s deleted submission: species %s, repository %s, accession %s' % (current_user.email, sub.species, repo, acc))

        sub.delete_dependencies(db)
        db.session.delete(sub)
        db.session.commit()
    return ''


@app.route('/submission/<id>', methods=['GET', 'POST'])
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not (sub.can_see(current_user) or current_user.has_role('Admin')):
        flash('Submission not found')
        return redirect('/submissions')

    (form, tables) = setup_submission_view_forms_and_tables(sub, db, sub.can_see_private(current_user))
    reviewer = (current_user.has_role(sub.species) or current_user in sub.delegates)

    if request.method == 'GET':
        return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump="", status=sub.submission_status, attachment=len(sub.notes_entries[0].attached_files) > 0)
    else:
        if not reviewer:
            flash('Submission not found')
            return redirect('/submissions')

        # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
        editable_tables = {'delegate_table': tables['delegate_table']}
        validation_result = process_table_updates(editable_tables, request, db)
        if validation_result.tag:
            if validation_result.valid:     # rebuild tables if something has changed
                (form, tables) = setup_submission_view_forms_and_tables(sub, db, sub.can_see_private(current_user))
            return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump = validation_result.tag, status=sub.submission_status)

        if form.validate():
            if form.action.data == 'draft':
                add_note(current_user, form.title.data, safe_textile('Submission returned to Submitter with the following message:\r\n\r\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission returned to Submitter', sub, db)
                send_mail('Submission %s returned to you from the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_returned', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s returned to Submitter by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_returned', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'draft'
                db.session.commit()
                flash('Submission returned to Submitter')
                return redirect('/submissions')
            elif form.action.data == 'complete':
                add_note(current_user, form.title.data, safe_textile('Submission completed with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission completed', sub, db)
                send_mail('Submission %s completed review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_completed', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s completed review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_completed', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'complete'
                db.session.commit()
                flash('Submission marked as complete')
                return redirect('/submissions')
            elif form.action.data == 'withdraw':
                referenced_gds = []
                for inf in sub.inferred_sequences:
                    for gd in inf.gene_descriptions:
                        if gd.status not in ('superceded', 'withdrawn'):
                            referenced_gds.append(gd.description_id)
                if len(referenced_gds) > 0:
                    flash('Please remove references to this submission in sequence(s) %s first.' % ','.join(referenced_gds))
                    return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump = validation_result.tag, status=sub.submission_status)
                add_note(current_user, form.title.data, safe_textile('Submission withdrawn with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission withdrawn', sub, db)
                send_mail('Submission %s has been marked as withdrawn by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_withdrawn', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s has been marked as withdrawn by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_withdrawn', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'withdrawn'
                db.session.commit()
                flash('Submission marked as withdrawn')
                return redirect('/submissions')
            elif form.action.data == 'review':
                add_note(current_user, form.title.data, safe_textile('Submission returned to IARC Review with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission returned to Review', sub, db)
                send_mail('Submission %s returned to review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_re_review', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s returned to review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_re_review', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'reviewing'
                db.session.commit()
                flash('Submission returned to Review')
                return redirect('/submissions')
            elif form.action.data == 'note':
                add_note(current_user, form.title.data, form.body.data, sub, db)
                db.session.commit()
                flash('Note Added')
                return redirect(url_for('submission', id=id, _anchor='review'))
            elif form.type.data == 'note':      #reply to thread
                head = db.session.query(JournalEntry).filter_by(submission_id = sub.id, type = 'note', id = int(form.action.data)).one_or_none()
                add_note(current_user, head.title, form.body.data, sub, db, parent_id=int(form.action.data))
                db.session.commit()
                flash('Note Added')
                return redirect(url_for('submission', id=id, _anchor='review'))
            else:
                return redirect('/submissions')

        else:
           return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump = validation_result.tag, status=sub.submission_status)



