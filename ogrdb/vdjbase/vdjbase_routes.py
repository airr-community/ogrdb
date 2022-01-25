import datetime
import json
import sys
from os import mkdir, remove
from os.path import isdir
from traceback import format_exc

from flask import request, render_template, redirect, url_for, flash, Response
from flask_login import current_user, login_required
from sqlalchemy import and_

from db.attached_file_db import AttachedFile, make_AttachedFile_table
from db.novel_vdjbase_db import NovelVdjbase
from db.vdjbase import update_from_vdjbase, setup_vdjbase_review_tables
from forms.attached_file_form import AttachedFileForm
from forms.notes_entry_form import NotesEntryForm
from forms.review_vdjbase_form import ReviewVdjbaseForm
from ogrdb.submission.submission_edit_form import EditableAttachedFileTable
from head import app, db, attach_path
from textile_filter import safe_textile


@app.route('/vdjbase_import', methods=['GET'])
def vdjbase_import():
    return update_from_vdjbase()


def can_edit_vdjbase_review(species):
    return current_user \
           and current_user.is_authenticated \
           and (current_user.has_role('AdminEdit') or (current_user.has_role(species)))


@app.route('/vdjbase_review', methods=['GET', 'POST'])
@app.route('/vdjbase_review/<selected_species>/<selected_locus>', methods=['GET', 'POST'])
def vdjbase_review(selected_species=None, selected_locus=None):
    form = ReviewVdjbaseForm()
    recs = db.session.query(NovelVdjbase.species, NovelVdjbase.locus).distinct().all()
    locus_choices = {}

    for (species, locus) in recs:
        if species not in locus_choices:
            locus_choices[species] = []
        if locus not in locus_choices[species]:
            locus_choices[species].append(locus)

    if selected_species and selected_locus:
        form.species.data = selected_species
        form.locus.data = selected_locus

    if request.method == 'POST' or (selected_species and selected_locus):
        if form.species.data in locus_choices and form.locus.data in locus_choices[form.species.data]:
            form.species.choices = [('Select', 'Select')]
            form.species.choices.extend([(s, s) for s in locus_choices.keys()])
            form.locus.choices = locus_choices[form.species.data]

            results = db.session.query(NovelVdjbase)\
                .filter(and_(NovelVdjbase.species == form.species.data, NovelVdjbase.locus == form.locus.data))\
                .all()

            editor = can_edit_vdjbase_review(form.species.data)
            table = setup_vdjbase_review_tables(results, editor)
            table.table_id = 'seq_table'
            return render_template('vdjbase_review.html',
                                   form=form,
                                   table=table,
                                   editor=editor,
                                   locus_choices=json.dumps(locus_choices))

    form.species.choices = [('Select', 'Select')]
    form.species.choices.extend([(s, s) for s in locus_choices.keys()])
    form.locus.choices = []
    return render_template('vdjbase_review.html',
                           form=form,
                           table=None,
                           locus_choices=json.dumps(locus_choices))


@app.route('/vdjbase_status', methods=['POST'])
@login_required
def vdjbase_status():
    form = request.form

    if form['value'] == form['current']:
        return form['current']

    try:
        row = db.session.query(NovelVdjbase).filter(NovelVdjbase.id == int(form['id'])).one_or_none()
    except:
        row = None

    if not row or not can_edit_vdjbase_review(row.species):
        return form['current']

    row.status = form['value']
    row.notes_entries[0].notes_text += '\r%s: Status was changed from %s to %s by %s' % \
                 (datetime.datetime.now().strftime("%d/%m/%y %H:%M"), form['current'], form['value'], current_user.name)
    row.last_updated = datetime.datetime.now()
    row.updated_by = current_user.name
    db.session.commit()

    return form['value']


@app.route('/vdjbase_review_detail/<id>', methods=['GET', 'POST'])
def vdjbase_review_detail(id):
    try:
        details = db.session.query(NovelVdjbase).filter(NovelVdjbase.id == int(id)).one_or_none()
    except:
        details = None

    if not details:
        return redirect(url_for('vdjbase_review'))

    form = NotesEntryForm(obj=details.notes_entries[0])
    editor = can_edit_vdjbase_review(details.species)

    if request.method == 'POST':
        if form.validate():
            if 'edit_btn' in request.form and can_edit_vdjbase_review(details.species):
                details.notes_entries[0].notes_text = request.form['notes_text'].encode('utf-8')
                db.session.commit()

            if 'notes_attachment' in request.files:
                for file in form.notes_attachment.data:
                    if file.filename != '':
                        af = None
                        for at in details.notes_entries[0].attached_files:
                            if at.filename == file.filename:
                                af = at
                                break
                        if af is None:
                            af = AttachedFile()
                            db.session.add(af)
                        af.notes_entry = details.notes_entries[0]
                        af.filename = file.filename
                        db.session.commit()
                        dirname = attach_path + 'V%5d' % details.id

                        try:
                            if not isdir(dirname):
                                mkdir(dirname)
                            with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                                fo.write(file.stream.read())
                        except:
                            info = sys.exc_info()
                            flash('Error saving attachment: %s' % (info[1]))
                            app.logger.error(format_exc())

            if 'close_btn' in request.form:
                return redirect(url_for('vdjbase_review', selected_species=details.species, selected_locus=details.locus))

    if editor:
        file_table = EditableAttachedFileTable(
            make_AttachedFile_table(details.notes_entries[0].attached_files),
            'attached_files',
            AttachedFileForm,
            details.notes_entries[0].attached_files,
            legend='Attachments',
            delete_route='delete_vdjbase_attachment',
            delete_message='Are you sure you wish to delete the attachment?',
            download_route='download_vdjbase_attachment')
    else:
        file_table = EditableAttachedFileTable(
            make_AttachedFile_table(details.notes_entries[0].attached_files),
            'attached_files',
            AttachedFileForm,
            details.notes_entries[0].attached_files,
            legend='Attachments',
            delete=False,
            download_route='download_vdjbase_attachment')

    return render_template('vdjbase_detail.html',
                           form=form,
                           header='%s (%s, %s)' % (details.vdjbase_name, details.species, details.locus),
                           notes=safe_textile(details.notes_entries[0].notes_text),
                           editor=editor,
                           file_table=file_table,
                           id=id)


@app.route('/download_vdjbase_attachment/<id>')
def download_vdjbase_attachment(id):
    att = db.session.query(AttachedFile).filter_by(id=id).one_or_none()
    if att is None:
        return redirect('/vdjbase_review')

    rec = att.notes_entry.novel_vdjbase

    try:
        dirname = attach_path + 'V%5d' % rec.id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/vdjbase_review')


@app.route('/delete_vdjbase_attachment/<id>', methods=['POST'])
def delete_vdjbase_attachment(id):
    att = db.session.query(AttachedFile).filter_by(id=id).one_or_none()
    if att is None:
        return redirect('/vdjbase_review')

    rec = att.notes_entry.novel_vdjbase
    if not can_edit_vdjbase_review(rec.species):
        return redirect('/vdjbase_review')

    try:
        dirname = attach_path + 'V%5d' % rec.id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


