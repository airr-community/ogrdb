import copy
import json
import sys
import datetime
from operator import attrgetter
from os import mkdir, remove
from os.path import isdir
from traceback import format_exc
import io

from flask import request, render_template, redirect, flash, url_for, Response
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from markupsafe import Markup
from sqlalchemy import and_, func, or_
from wtforms import ValidationError

from head import app, db, attach_path

from db.attached_file_db import AttachedFile
from db.gene_description_db import GeneDescription
from db.germline_set_db import GermlineSet, save_GermlineSet, copy_GermlineSet
from db.journal_entry_db import JournalEntry, copy_JournalEntry
from db.misc_db import Committee
from db.notes_entry_db import NotesEntry

from forms.aggregate_form import AggregateForm
from forms.germline_set_form import GermlineSetForm
from forms.germline_set_gene_form import NewGermlineSetGeneForm
from forms.germline_set_new_form import NewGermlineSetForm
from forms.journal_entry_form import JournalEntryForm
from forms.notes_entry_form import NotesEntryForm
from ogrdb.germline_set.descs_to_fasta import descs_to_fasta

from ogrdb.sequence.sequence_list_table import setup_sequence_list_table
from ogrdb.sequence.sequence_routes import publish_sequence
from ogrdb.submission.submission_edit_form import process_table_updates
from ogrdb.submission.submission_view_form import HiddenReturnForm

from ogrdb.germline_set.germline_set_list_table import setup_germline_set_list_table, setup_published_germline_set_list_info
from ogrdb.germline_set.germline_set_table import setup_germline_set_edit_tables, list_germline_set_changes
from ogrdb.germline_set.germline_set_view_form import setup_germline_set_view_tables

from textile_filter import safe_textile
from ogrdb.germline_set.to_airr import germline_set_to_airr

from journal import add_history
from mail import send_mail

import zenodo


@app.route('/germline_sets/<species>', methods=['GET', 'POST'])
def germline_sets(species):
    tables = {}
    show_withdrawn = False

    if current_user.is_authenticated:
        if current_user.has_role(species):
            if 'withdrawn' in request.args and request.args['withdrawn'] == 'yes':
                q = db.session.query(GermlineSet).filter(GermlineSet.species == species).filter(GermlineSet.status.in_(['draft', 'withdrawn']))
                show_withdrawn = True
            else:
                q = db.session.query(GermlineSet).filter(GermlineSet.species == species).filter(GermlineSet.status.in_(['draft']))
                show_withdrawn = False
            results = q.all()

            tables['species'] = {species: {}}
            tables['species'][species]['draft'] = setup_germline_set_list_table(results, current_user)
            tables['species'][species]['draft'].table_id = species + '_draft'

    q = db.session.query(GermlineSet)\
        .filter(GermlineSet.species == species)\
        .filter(GermlineSet.status == 'published')\
        .order_by(GermlineSet.species_subgroup, GermlineSet.locus)

    results = q.all()

    affirmed = setup_published_germline_set_list_info(results, current_user, species=='Human')

    foo =  render_template('germline_set_list.html', tables=tables, species=species, affirmed=affirmed, show_withdrawn=show_withdrawn, any_published=(len(affirmed.items) > 0))
    return foo


@app.route('/new_germline_set/<species>', methods=['GET', 'POST'])
@login_required
def new_germline_set(species):
    if not current_user.has_role(species):
        return redirect('/')

    form = NewGermlineSetForm()
    form.locus.choices = ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRG', 'TRD']

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('germline_sets', species=species))

        if form.validate():
            try:
                if db.session.query(GermlineSet).filter(and_(GermlineSet.species == species, GermlineSet.germline_set_name == form.name.data, ~GermlineSet.status.in_(['withdrawn', 'superceded']))).count() > 0:
                    form.name.errors = ['A germline set already exists with that name.']
                    raise ValidationError()

                germline_set = GermlineSet()
                germline_set.species = species
                germline_set.status = 'draft'
                germline_set.author = current_user.name
                germline_set.lab_address = current_user.address
                germline_set.release_version = 0
                germline_set.locus = form.locus.data
                germline_set.germline_set_name = form.name.data

                db.session.add(germline_set)
                db.session.commit()
                germline_set.germline_set_id = "G%05d" % germline_set.id
                add_history(current_user, '%s germline set %s (%s) created' % (germline_set.species, germline_set.germline_set_id, germline_set.germline_set_name), germline_set, db)
                db.session.commit()

                return redirect(url_for('germline_sets', species=species))

            except ValidationError as e:
                return render_template('germline_set_new.html', form=form, species=species)

    return render_template('germline_set_new.html', form=form, species=species)


@app.route('/edit_germline_set/<id>', methods=['GET', 'POST'])
@login_required
def edit_germline_set(id):
    germline_set = check_set_edit(id)
    if germline_set is None:
        return redirect('/')

    if len(germline_set.notes_entries) == 0:
        germline_set.notes_entries.append(NotesEntry())
        db.session.commit()

    update_germline_set_seqs(germline_set)
    db.session.commit()

    tables = setup_germline_set_edit_tables(db, germline_set)
    tables['genes'].table_id = "genetable"
    tables['genes'].html_attrs = {'style': 'width: 100%'}
    germline_set_form = GermlineSetForm(obj=germline_set)
    notes_entry_form = NotesEntryForm(obj=germline_set.notes_entries[0])
    history_form = JournalEntryForm()
    hidden_return_form = HiddenReturnForm()
    changes = list_germline_set_changes(germline_set)
    form = AggregateForm(germline_set_form, notes_entry_form, history_form, hidden_return_form, tables['ack'].form, tables['pubmed_table'].form)

    if request.method == 'POST':
        form.validate()
        valid = True

        for field in form._fields:
            if len(form[field].errors) > 0:
                if field in history_form._fields and 'history_btn' not in request.form:
                    form[field].errors = []
                else:
                    valid = False

        if form.action.data == 'published':
            if len(germline_set.gene_descriptions) < 1:
                flash("Please add at least one gene to the set!")
                form.action.data = ''
                valid = False

            sequences = {}
            
            for gene_description in germline_set.gene_descriptions:
                if gene_description.coding_seq_imgt not in sequences:
                    sequences[gene_description.coding_seq_imgt] = []
                sequences[gene_description.coding_seq_imgt].append(gene_description.sequence_name)

                if gene_description.status == 'draft':
                    publish_sequence(gene_description, form.body.data, False)
                if gene_description.status == 'published' and gene_description.affirmation_level == 0:
                    flash("Can't publish this set while gene %s is at affirmation level 0." % gene_description.sequence_name)
                    form.action.data = ''
                    valid = False
                if gene_description.status == 'withdrawn':
                    flash("Can't publish this set while gene %s is withdrawn." % gene_description.sequence_name)
                    form.action.data = ''
                    valid = False
                if (gene_description.species_subgroup or germline_set.species_subgroup) and (gene_description.species_subgroup != germline_set.species_subgroup or gene_description.species_subgroup_type != germline_set.species_subgroup_type):
                    flash("Can't publish this set while gene %s species subgroup/subgroup type disagreees with the germline set values." % gene_description.sequence_name)
                    form.action.data = ''
                    valid = False
            
            # assign paralogs
            for gene_description in germline_set.gene_descriptions:
                gene_description.paralogs = ','.join([x for x in sequences[gene_description.coding_seq_imgt] if x != gene_description.sequence_name])
            db.session.commit()

        if valid:
            try:
                validation_result = process_table_updates({'ack': tables['ack'], 'pubmed_table': tables['pubmed_table']}, request, db)
                if not validation_result.valid:
                    raise ValidationError()

                save_GermlineSet(db, germline_set, form)

                if 'add_gene_btn' in request.form:
                    return redirect(url_for('add_gene_to_set', id=id))

                if form.action.data == 'published':
                    old_set = db.session.query(GermlineSet).filter_by(germline_set_id=germline_set.germline_set_id, status='published').one_or_none()
                    if old_set:
                        old_set.status = 'superceded'

                    max_version = db.session.query(func.max(GermlineSet.release_version))\
                        .filter(GermlineSet.germline_set_id == germline_set.germline_set_id)\
                        .filter(or_(GermlineSet.status == 'withdrawn', GermlineSet.status == 'superceded'))\
                        .one_or_none()

                    germline_set.release_version = max_version[0] + 1 if max_version[0] else 1
                    germline_set.release_date = datetime.date.today()

                    hist_notes = form.body.data
                    changes = list_germline_set_changes(germline_set)   # to get updated versions
                    if changes != '':
                        hist_notes += Markup('<br>') + changes

                    add_history(current_user, 'Version %s published' % (germline_set.release_version), germline_set, db, body=hist_notes)
                    send_mail('Germline set %s version %d published by the IARC %s Committee' % (germline_set.germline_set_id, germline_set.release_version, germline_set.species), [germline_set.species], 'iarc_germline_set_released', reviewer=current_user, user_name=germline_set.author, germline_set=germline_set, comment=form.body.data)

                    germline_set.zenodo_current_deposition = ''
                    germline_set.doi = ''
                    germline_set.status = 'published'
                    db.session.commit()
                    flash('Germline set published')
                    return redirect(url_for('germline_sets', species=germline_set.species))

                if 'notes_attachment' in request.files:
                    for file in form.notes_attachment.data:
                        if file.filename != '':
                            af = None
                            for at in germline_set.notes_entries[0].attached_files:
                                if at.filename == file.filename:
                                    af = at
                                    break
                            if af is None:
                                af = AttachedFile()
                            af.notes_entry = germline_set.notes_entries[0]
                            af.filename = file.filename
                            db.session.add(af)
                            db.session.commit()
                            dirname = attach_path + germline_set.germline_set_id

                            try:
                                if not isdir(dirname):
                                    mkdir(dirname)
                                with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                                    fo.write(file.stream.read())
                            except:
                                info = sys.exc_info()
                                flash('Error saving attachment: %s' % (info[1]))
                                app.logger.error(format_exc())
                                return redirect(url_for('edit_submission', id=germline_set.germline_set_id))
                            db.session.commit()
                            validation_result.tag = 'notes'

                if 'notes_text' in request.form and germline_set.notes_entries[0].notes_text is None or germline_set.notes_entries[0].notes_text != request.form['notes_text'].encode('utf-8'):
                    germline_set.notes_entries[0].notes_text = request.form['notes_text'].encode('utf-8')
                    db.session.commit()

            except ValidationError:
                return render_template('germline_set_edit.html',
                                       form=form,
                                       germline_set_name=germline_set.germline_set_name,
                                       id=id,
                                       set_id=germline_set.germline_set_id,
                                       tables=tables,
                                       changes=changes,
                                       jump=validation_result.tag,
                                       version=germline_set.release_version)

            if validation_result.tag:
                return redirect(url_for('edit_germline_set', id=id, _anchor=validation_result.tag))
            else:
                return redirect(url_for('germline_sets', species=germline_set.species))

        else:
            for field in tables['ack'].form:
                if len(field.errors) > 0:
                    return render_template('germline_set_edit.html',
                                           form=form,
                                           germline_set_name=germline_set.germline_set_name,
                                           id=id,
                                           set_id=germline_set.germline_set_id,
                                           tables=tables,
                                           changes=changes,
                                           jump='ack',
                                           version=germline_set.release_version)

    return render_template('germline_set_edit.html',
                           form=form,
                           germline_set_name=germline_set.germline_set_name,
                           id=id,
                           set_id=germline_set.germline_set_id,
                           tables=tables,
                           version=germline_set.release_version,
                           changes=changes,
                           )


def check_set_view(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id=id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if not set.can_see(current_user):
            flash('You do not have rights to view that sequence.')

        return set

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


def check_set_edit(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if not set.can_edit(current_user):
            flash('You do not have rights to edit that sequence.')
            return None

        return set

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


@app.route('/delete_germline_set/<id>', methods=['POST'])
@login_required
def delete_germline_set(id):
    set = check_set_edit(id)
    if set is not None:
        set.delete_dependencies(db)
        db.session.delete(set)
        db.session.commit()
    return ''


@app.route('/download_germline_set_attachment/<id>')
def download_germline_set_attachment(id):
    att = check_germline_set_attachment_view(id)
    if att is None:
        return redirect('/')

    germline_set = att.notes_entry.germline_set

    try:
        dirname = attach_path + germline_set.germline_set_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_germline_set_attachment/<id>', methods=['POST'])
def delete_germline_set_attachment(id):
    att = check_germline_set_attachment_edit(id)
    if att is None:
        return redirect('/')

    germline_set = att.notes_entry.submission

    try:
        dirname = attach_path + germline_set.germline_set_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


def check_set_draft(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if set.status != 'published':
            flash('Only published germline sets can be cloned.')
            return None

        clones = db.session.query(GermlineSet).filter_by(germline_set_name=set.germline_set_name).all()
        for clone in clones:
            if clone.status == 'draft':
                flash('There is already a draft of that germline set')
                return None

        if not set.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return set


def check_set_zenodo(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if set.status != 'published':
            flash('Only published germline sets can be deposited.')
            return None

        if not set.can_draft(current_user):
            flash('You do not have rights to deposit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return set


@app.route('/draft_germline_set/<id>', methods=['POST'])
@login_required
def draft_germline_set(id):
    set = check_set_draft(id)
    if set is not None:
        new_set = GermlineSet()
        db.session.add(new_set)
        db.session.commit()

        copy_GermlineSet(set, new_set)
        new_set.status = 'draft'
        new_set.release_version = 0
        new_set.zenodo_current_deposition = ''
        new_set.doi = ''

        for gene_description in set.gene_descriptions:
            new_set.gene_descriptions.append(gene_description)

        new_set.notes_entries.append(NotesEntry())
        new_set.notes_entries[0].notes_text = set.notes_entries[0].notes_text

        for af in set.notes_entries[0].attached_files:
            new_af = AttachedFile()
            new_af.notes_entry = new_set.notes_entries[0]
            new_af.filename = af.filename
            db.session.add(af)

        for journal_entry in set.journal_entries:
            new_entry = JournalEntry()
            copy_JournalEntry(journal_entry, new_entry)
            new_set.journal_entries.append(new_entry)

        update_germline_set_seqs(new_set)

        db.session.commit()
    return ''


def check_set_withdraw(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id=id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if set.status != 'published':
            flash('Only published sequences can be withdrawn.')
            return None

        if not set.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return set


def update_germline_set_seqs(germline_set):
    for desc in list(germline_set.gene_descriptions):
        gd = db.session.query(GeneDescription).filter(GeneDescription.description_id == desc.description_id, GeneDescription.status == 'draft').one_or_none()
        if gd is None:
            gd = db.session.query(GeneDescription).filter(GeneDescription.description_id == desc.description_id, GeneDescription.status == 'published').one_or_none()
        if gd and gd != desc:
            germline_set.gene_descriptions.remove(desc)
            germline_set.gene_descriptions.append(gd)


@app.route('/withdraw_germline_set/<id>', methods=['POST'])
@login_required
def withdraw_germline_set(id):
    set = check_set_withdraw(id)
    if set is not None:
        add_history(current_user, 'Published version %s withdrawn' % set.release_version, set, db, body='')
        send_mail('Germline set %s version %d withdrawn by the IARC %s Committee' % (set.germline_set_id, set.release_version, set.species), [set.species], 'iarc_germline_set_withdrawn', reviewer=current_user, user_name=set.author, germline_set=set, comment='')
        set.status = 'withdrawn'
        db.session.commit()
        flash('Germline set %s withdrawn' % set.germline_set_name)

        db.session.commit()

    return ''


@app.route('/delete_gene_from_set', methods=['POST'])
@login_required
def delete_gene_from_set():
    germline_set = check_set_edit(request.form['set_id'])
    if germline_set is not None:
        gene_description = db.session.query(GeneDescription).filter(GeneDescription.id == request.form['gene_id']).one_or_none()
        if gene_description is not None and gene_description in germline_set.gene_descriptions:
            germline_set.gene_descriptions.remove(gene_description)
            db.session.commit()

    return ''


@app.route('/add_gene_to_set/<id>', methods=['GET', 'POST'])
@login_required
def add_gene_to_set(id):
    germline_set = check_set_edit(id)
    if germline_set is None:
        return redirect('/')

    form = NewGermlineSetGeneForm()
    gene_descriptions = db.session.query(GeneDescription).filter(GeneDescription.species == germline_set.species)\
        .filter(GeneDescription.status.in_(['published', 'draft']))

    if germline_set.species_subgroup:
        gene_descriptions = gene_descriptions.filter(GeneDescription.species_subgroup == germline_set.species_subgroup)

    gene_descriptions = gene_descriptions.all()

    gene_descriptions = [g for g in gene_descriptions if g not in germline_set.gene_descriptions]
    gene_descriptions = [g for g in gene_descriptions if germline_set.locus == g.locus]
    gene_descriptions.sort(key=attrgetter('sequence_name'))
    form.create.label.text = "Add"

    gene_table = setup_sequence_list_table(gene_descriptions, current_user, edit=False)
    gene_table.table_id = "genetable"
    gene_table.html_attrs = {'style': 'width: 100%'}

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

        if form.validate():
            selected = form.results.data.split(',')
            selected_ids = []

            for sel in selected:
                if "/sequence/" in sel:
                    try:
                        selected_ids.append(int(sel.split("/sequence/")[1].split('">')[0]))
                    except:
                        pass

            for gid in selected_ids:
                gene_description = db.session.query(GeneDescription).filter(GeneDescription.id == gid).one_or_none()

                if gene_description and gene_description not in germline_set.gene_descriptions:
                    germline_set.gene_descriptions.append(gene_description)

            db.session.commit()
        return redirect(url_for('edit_germline_set', id=id, _anchor='genes'))

    return render_template('germline_set_add_gene.html', form=form, name=germline_set.germline_set_name, gene_table=gene_table, id=id)


def check_germline_set_attachment_edit(af_id):
    af = db.session.query(AttachedFile).filter_by(id=af_id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    germline_set = af.notes_entry.germline_set
    if not germline_set.can_edit(current_user):
        flash('You do not have rights to delete that attachment')
        return None
    return af


def check_germline_set_attachment_view(af_id):
    af = db.session.query(AttachedFile).filter_by(id=af_id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    germline_set = af.notes_entry.germline_set
    if not germline_set.can_see(current_user):
        flash('You do not have rights to download that attachment')
        return None
    return af


@app.route('/download_germline_set_attachment/<id>')
def download_germline_set_attachment_view(id):
    att = check_germline_set_attachment_view(id)
    if att is None:
        return redirect('/')

    germline_set = att.notes_entry.germline_set

    try:
        dirname = attach_path + germline_set.germline_set_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_submission_attachment/<id>', methods=['POST'])
def delete_set_attachment(id):
    att = check_germline_set_attachment_edit(id)
    if att is None:
        return redirect('/')

    sub = att.notes_entry.submission

    try:
        dirname = attach_path + germline_set.germline_set_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


@app.route('/germline_set/<id>', methods=['GET'])
def germline_set(id):
    germline_set = check_set_view(id)
    if germline_set is None:
        return redirect('/')

    if len(germline_set.notes_entries) == 0:
        germline_set.notes_entries.append(NotesEntry())
        db.session.commit()

    form = FlaskForm()
    tables = setup_germline_set_view_tables(db, germline_set, current_user.has_role(germline_set.species))
    tables['genes'].table_id = "genetable"
    tables['genes'].html_attrs = {'style': 'width: 100%'}
    versions = db.session.query(GermlineSet).filter(GermlineSet.species == germline_set.species)\
        .filter(GermlineSet.germline_set_name == germline_set.germline_set_name)\
        .filter(GermlineSet.status.in_(['published', 'superceded']))\
        .all()
    tables['versions'] = setup_germline_set_list_table(versions, None)
    supplementary_files = len(tables['attachments'].table.items) > 0

    notes = safe_textile(germline_set.notes_entries[0].notes_text)
    return render_template('germline_set_view.html', form=form, tables=tables, name=germline_set.germline_set_name, supplementary_files=supplementary_files, notes=notes, id=id)


@app.route('/download_germline_set/<set_id>/<format>')
def download_germline_set(set_id, format):
    if format not in ['gapped', 'ungapped', 'airr', 'gapped_ex', 'ungapped_ex', 'airr_ex']:
        flash('Invalid format')
        return redirect('/')

    germline_set = check_set_view(set_id)
    if not germline_set:
        flash('Germline set not found')
        return redirect('/')

    if len(germline_set.gene_descriptions) < 1:
        flash('No sequences to download')
        return redirect('/')
    
    extend = False
    if '_ex' in format:
        extend = True

    if 'airr' in format:
        dl = json.dumps(germline_set_to_airr(germline_set, extend), default=str, indent=4)
        filename = '%s_%s_rev_%d.json' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version)
    else:
        dl = descs_to_fasta(germline_set.gene_descriptions, format, fake_allele=True, extend=extend)
        filename = '%s_%s_rev_%d_%s.fasta' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, format)

    return Response(dl, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})


zenodo_metadata_template = {
    'access_right': 'open',
    'communities': [{'identifier': 'zenodo'}],
    'creators': [{'affiliation': 'Birkbeck College', 'name': 'Lees, William', 'orcid': '0000-0001-9834-6840'}],
    'description': '<p>Germline Reference set published on the Open Germline Receptor Database (OGRDB)</p>',
    'keywords': ['Receptor germline set', 'AIRR-seq', 'AIRR Community', 'Receptor Repertoire', 'Immunology'],
    'license': 'other-open',
    'related_identifiers': [{'identifier': 'https://ogrdb.airr-community.org/', 'relation': 'isPublishedIn', 'resource_type': 'dataset', 'scheme': 'url'}],
    'title': 'IG receptor Mouse Germline Set IGKJ (all strains)',
    'upload_type': 'dataset',
    'version': '1'
}

def make_files_for_zenodo(germline_set):
    filenames = []
    filedesc_pairs = []

    filenames.append(app.config['ZENODO_COPYRIGHT_FILE'])

    for af in germline_set.notes_entries[0].attached_files:
        dirname = attach_path + germline_set.germline_set_id
        fp = open(dirname + '/multi_attachment_%s' % af.id, 'rb')
        filedesc_pairs.append((fp, af.filename))
        info = sys.exc_info()

    fp = io.StringIO(json.dumps(germline_set_to_airr(germline_set), default=str, indent=4))
    filename = '%s_%s_rev_%d.json' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version)
    filedesc_pairs.append((fp, filename))

    fp = io.StringIO(descs_to_fasta(germline_set.gene_descriptions, 'gapped'))
    filename = '%s_%s_rev_%d_%s.fasta' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, 'gapped')
    filedesc_pairs.append((fp, filename))

    fp = io.StringIO(descs_to_fasta(germline_set.gene_descriptions, 'ungapped'))
    filename = '%s_%s_rev_%d_%s.fasta' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, 'ungapped')
    filedesc_pairs.append((fp, filename))

    return filenames, filedesc_pairs


@app.route('/create_germline_set_doi_series/<set_id>', methods=['GET', 'POST'])
def create_germline_set_doi_series(set_id):
    germline_set = check_set_zenodo(set_id)
    if germline_set is None:
        return redirect('/')

    if germline_set.zenodo_base_deposition is not None and len(germline_set.zenodo_base_deposition) > 0:
        flash('A base deposition id already exists')
        return ''

    zenodo_url = app.config['ZENODO_URL']
    zenodo_access_token = app.config['ZENODO_ACCESS_TOKEN']

    try:
        subgroup = 'subgroup: ' + germline_set.species_subgroup if germline_set.species_subgroup else ''
        sub_metadata = copy.deepcopy(zenodo_metadata_template)
        receptor_type = germline_set.locus[:2]
        title = f"{receptor_type} receptor germline set for species: {germline_set.species} {subgroup} set_name: {germline_set.germline_set_name}"
        sub_metadata['title'] = title

        if receptor_type == 'IG':
            sub_metadata['keywords'].extend(['Antibody', 'B cell', 'IG receptor'])
        else:
            sub_metadata['keywords'].extend(['T cell', 'T cell receptor'])

        success_status, resp = zenodo.zenodo_new_deposition(zenodo_url, zenodo_access_token, sub_metadata)

        if not success_status:
            flash(resp)
            return ''

        deposition_id = resp
        germline_set.zenodo_base_deposition = deposition_id
        filenames, filedescs = make_files_for_zenodo(germline_set)
        db.session.commit()

        success_status, resp = zenodo.zenodo_new_version(zenodo_url, zenodo_access_token, deposition_id, filenames, filedescs, str(germline_set.release_version))
        if not success_status:
            flash(resp)
            return ''

        germline_set.zenodo_current_deposition = resp['id']
        germline_set.doi = resp['doi']
        db.session.commit()
        flash('Deposition succeeded')
        return ''

    except Exception as e:
        flash(str(e))
        return ''

    return ''


@app.route('/update_germline_set_doi/<set_id>', methods=['GET', 'POST'])
def update_germline_set_doi(set_id):
    germline_set = check_set_zenodo(set_id)
    if germline_set is None:
        return redirect('/')

    if germline_set.zenodo_current_deposition is None or len(germline_set.zenodo_current_deposition) > 0:
        flash('A deposition id already exists')
        return ''

    zenodo_url = app.config['ZENODO_URL']
    zenodo_access_token = app.config['ZENODO_ACCESS_TOKEN']

    try:
        filenames, filedescs = make_files_for_zenodo(germline_set)

        success_status, resp = zenodo.zenodo_new_version(zenodo_url, zenodo_access_token, germline_set.zenodo_base_deposition, filenames, filedescs, str(germline_set.release_version))
        if not success_status:
            flash(resp)
            return ''

        germline_set.zenodo_current_deposition = resp['id']
        germline_set.doi = resp['doi']
        db.session.commit()
        flash('Deposition succeeded')
        return ''

    except Exception as e:
        flash(str(e))
        return ''

    return ''