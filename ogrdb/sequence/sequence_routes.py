# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE

import csv
import datetime
import io
import json
import os
import sys
from os import mkdir, remove
from os.path import isdir
from traceback import format_exc
import shutil

from flask import flash, redirect, request, render_template, url_for, Response
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import and_
from wtforms import ValidationError

from head import db, app, attach_path


from db.attached_file_db import AttachedFile
from db.dupe_gene_note_db import DupeGeneNote
from db.gene_description_db import GeneDescription, GenomicSupport, save_GenomicSupport, populate_GenomicSupport, save_GeneDescription, copy_GeneDescription
from db.genotype_db import Genotype
from db.inferred_sequence_db import InferredSequence
from db.journal_entry_db import JournalEntry, copy_JournalEntry
from db.misc_db import Committee
from db.repertoire_db import Acknowledgements
from db.submission_db import Submission
from db.novel_vdjbase_db import NovelVdjbase

from forms.aggregate_form import AggregateForm
from forms.gene_description_form import GenomicSupportForm, GeneDescriptionForm
from forms.gene_description_notes_form import GeneDescriptionNotesForm
from forms.journal_entry_form import JournalEntryForm
from forms.sequence_new_form import NewSequenceForm
from forms.sequences_species_form import SpeciesForm
from imgt.imgt_ref import get_imgt_reference_genes
from ogrdb.germline_set.descs_to_fasta import descs_to_fasta

from ogrdb.submission.inferred_sequence_routes import validate_ext
from ogrdb.submission.submission_edit_form import process_table_updates
from ogrdb.submission.submission_routes import check_sub_view
from ogrdb.submission.submission_view_form import HiddenReturnForm

from ogrdb.sequence.sequence_view_form import setup_sequence_view_tables
from ogrdb.sequence.inferred_sequence_table import setup_sequence_edit_tables
from ogrdb.sequence.sequence_list_table import setup_sequence_list_table, setup_sequence_version_table

from textile_filter import safe_textile
from journal import add_history, add_note
from mail import send_mail
from ogrdb.germline_set.to_airr import AIRRAlleleDescription


def check_seq_view(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id=id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if not desc.can_see(current_user):
            flash('You do not have rights to view that sequence.')

        return desc

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


def check_seq_edit(seq_id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id=seq_id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if not desc.can_edit(current_user):
            flash('You do not have rights to edit that sequence.')
            return None

        return desc

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


def check_seq_see_notes(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if not desc.can_see_notes(current_user):
            flash('You do not have rights to view notes.')
            return None

        return desc

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


def check_seq_attachment_edit(id):
    af = db.session.query(AttachedFile).filter_by(id=id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    seq = af.gene_description
    if not seq.can_edit(current_user):
        flash('You do not have rights to delete that attachment')
        return None
    return af


def check_seq_attachment_view(id):
    af = db.session.query(AttachedFile).filter_by(id = id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    seq = af.gene_description
    if not seq.can_see(current_user):
        flash('You do not have rights to download that attachment')
        return None
    return af


def check_seq_draft(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if desc.status != 'published':
            flash('Only published sequences can be cloned.')
            return None

        clones = db.session.query(GeneDescription).filter_by(sequence_name = desc.sequence_name).all()
        for clone in clones:
            if clone.status == 'draft':
                flash('There is already a draft of that sequence')
                return None

        if not desc.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc


def check_seq_withdraw(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if desc.status != 'published':
            flash('Only published sequences can be withdrawn.')
            return None

        if not desc.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc


@app.route('/sequences/<sp>', methods=['GET', 'POST'])
def sequences(sp):
    tables = {}
    show_withdrawn = False

    species = [s[0] for s in db.session.query(Committee.species).all()]

    if sp not in species:
        return redirect('/')

    if current_user.is_authenticated:
        if current_user.has_role(sp):
            if 'species' not in tables:
                tables['species'] = {}
            tables['species'][sp] = {}

            if 'withdrawn' in request.args and request.args['withdrawn'] == 'yes':
                q = db.session.query(GeneDescription).filter(GeneDescription.species == sp).filter(GeneDescription.status.in_(['draft', 'withdrawn']))
                show_withdrawn = True
            else:
                q = db.session.query(GeneDescription).filter(GeneDescription.species == sp).filter(GeneDescription.status.in_(['draft']))
                show_withdrawn = False
            results = q.all()

            tables['species'][sp]['draft'] = setup_sequence_list_table(results, current_user)
            tables['species'][sp]['draft'].table_id = sp + '_draft'

            q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level == '0')
            results = q.all()
            tables['species'][sp]['level_0'] = setup_sequence_list_table(results, current_user)
            tables['species'][sp]['level_0'].table_id = sp + '_level_0'

    q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level != '0')
    results = q.all()
    tables['affirmed'] = setup_sequence_list_table(results, current_user)
    tables['affirmed'].table_id = 'affirmed'

    if len(db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.affirmation_level != '0', GeneDescription.species == sp).all()) >= 1:
        form = SpeciesForm()
        form.species.choices = [sp]
    else:
        form = None

    return render_template('sequence_list.html', tables=tables, show_withdrawn=show_withdrawn, form=form)


def copy_acknowledgements(seq, gene_description):
    def add_acknowledgement_to_gd(name, institution_name, orcid_id, gene_description):
        for ack in gene_description.acknowledgements:
            if ack.ack_name == name and ack.ack_institution_name == institution_name:
                return

        a = Acknowledgements()
        a.ack_name = name
        a.ack_institution_name = institution_name
        a.ack_ORCID_id = orcid_id
        gene_description.acknowledgements.append(a)

    add_acknowledgement_to_gd(seq.submission.submitter_name, seq.submission.submitter_address, '', gene_description)

    # Copy acknowledgements across

    for ack in seq.submission.acknowledgements:
        add_acknowledgement_to_gd(ack.ack_name, ack.ack_institution_name, ack.ack_ORCID_id, gene_description)


@app.route('/new_sequence/<species>', methods=['GET', 'POST'])
@login_required
def new_sequence(species):
    if not current_user.has_role(species):
        return redirect('/')

    form = NewSequenceForm()
    subs = db.session.query(Submission).filter(Submission.species==species).filter(Submission.submission_status.in_(['reviewing', 'complete', 'published'])).all()
    form.submission_id.choices = [('', 'Select Submission')] +  [(s.submission_id, '%s (%s)' % (s.submission_id, s.submitter_name)) for s in subs]
    form.sequence_name.choices = [(0, 'Select Sequence')]

    if request.method == 'POST':        # Don't use form validation because the selects are dynamically updated
        if form.cancel.data:
            return redirect(url_for('sequences', sp=species))

        if form.upload_file.data:
            return upload_sequences(form, species)

        try:
            if form.new_name.data is None or len(form.new_name.data) < 1:
                form.new_name.errors = ['Name cannot be blank.']
                raise ValidationError()

            if db.session.query(GeneDescription).filter(
                    and_(GeneDescription.species == species,
                         GeneDescription.sequence_name == form.new_name.data,
                         GeneDescription.species_subgroup == form.new_name.data,
                         ~GeneDescription.status.in_(['withdrawn', 'superceded']))).count() > 0:
                form.new_name.errors = ['A sequence already exists with that name.']
                raise ValidationError()

            record_type = request.form['record_type']
            if record_type == 'submission':
                if form.submission_id.data == '0' or form.submission_id.data == '' or form.submission_id.data == 'None':
                    form.submission_id.errors = ['Please select a submission.']
                    raise ValidationError()

                if form.sequence_name.data == '0' or form.sequence_name.data == '' or form.sequence_name.data == 'None':
                    form.sequence_name.errors = ['Please select a sequence.']
                    raise ValidationError()

                sub = db.session.query(Submission).filter_by(submission_id = form.submission_id.data).one_or_none()
                if sub.species != species or sub.submission_status not in ('reviewing', 'published', 'complete'):
                    return redirect(url_for('sequences', sp=species))

                seq = db.session.query(InferredSequence).filter_by(id = int(form.sequence_name.data)).one_or_none()

                if seq is None or seq not in sub.inferred_sequences:
                    return redirect(url_for('sequences', sp=species))

            gene_description = GeneDescription()
            gene_description.sequence_name = form.new_name.data
            gene_description.species = species
            gene_description.species_subgroup = form.species_subgroup.data
            gene_description.status = 'draft'
            gene_description.maintainer = current_user.name
            gene_description.lab_address = current_user.address
            gene_description.functionalionality = 'F'
            gene_description.inference_type = 'Rearranged Only' if record_type == 'submission' else 'Unrearranged Only'
            gene_description.release_version = 1
            gene_description.affirmation_level = 0

            if record_type == 'submission':
                gene_description.inferred_sequences.append(seq)
                gene_description.inferred_extension = seq.inferred_extension
                gene_description.ext_3prime = seq.ext_3prime
                gene_description.start_3prime_ext = seq.start_3prime_ext
                gene_description.end_3prime_ext = seq.end_3prime_ext
                gene_description.ext_5prime = seq.ext_5prime
                gene_description.start_5prime_ext = seq.start_5prime_ext
                gene_description.end_5prime_ext = seq.end_5prime_ext
                gene_description.sequence = seq.sequence_details.nt_sequence
                gene_description.locus = seq.genotype_description.locus
                gene_description.sequence_type = seq.genotype_description.sequence_type
                gene_description.coding_seq_imgt = seq.sequence_details.nt_sequence_gapped if gene_description.sequence_type == 'V' else seq.sequence_details.nt_sequence
                copy_acknowledgements(seq, gene_description)
            else:
                gene_description.inferred_extension = False
                gene_description.ext_3prime = None
                gene_description.start_3prime_ext = None
                gene_description.end_3prime_ext = None
                gene_description.ext_5prime = None
                gene_description.start_5prime_ext = None
                gene_description.end_5prime_ext = None
                gene_description.sequence = ''
                gene_description.locus = ''
                gene_description.sequence_type = 'V'
                gene_description.coding_seq_imgt = ''

                parse_name_to_gene_description(gene_description)

            db.session.add(gene_description)
            db.session.commit()
            gene_description.description_id = "A%05d" % gene_description.id
            db.session.commit()
            if record_type == 'submission':
                gene_description.build_duplicate_list(db, seq.sequence_details.nt_sequence)
            return redirect(url_for('sequences', sp=species))

        except ValidationError as e:
            return render_template('sequence_new.html', form=form, species=species)


    return render_template('sequence_new.html', form=form, species=species)


# Parse the name, if it's tractable
def parse_name_to_gene_description(gene_description):
    try:
        sn = gene_description.sequence_name
        if sn[:2] == 'IG' or sn[:2] == 'TR':
            gene_description.locus = sn[:3]
            gene_description.sequence_type = sn[3]
            if '-' in sn:
                if '*' in sn:
                    snq = sn.split('*')
                    gene_description.allele_designation = snq[1]
                    sn = snq[0]
                else:
                    gene_description.allele_designation = ''
                snq = sn.split('-')
                gene_description.subgroup_designation = snq[len(snq) - 1]
                del (snq[len(snq) - 1])
                gene_description.gene_subgroup = '-'.join(snq)[4:]
            elif '*' in sn:
                snq = sn.split('*')
                gene_description.gene_subgroup = snq[0][4:]
                gene_description.allele_designation = snq[1]
            else:
                gene_description.gene_subgroup = sn[4:]
    except:
        pass

def upload_sequences(form, species):
    # check file
    errors = []
    fi = io.StringIO(form.upload_file.data.read().decode("utf-8"))
    reader = csv.DictReader(fi)
    required_headers = ['gene_label', 'imgt', 'functionality', 'type', 'inference_type', 'sequence', 'sequence_gapped', 'species_subgroup', 'subgroup_type', 'alt_names', 'affirmation']
    headers = None
    row_count = 2
    for row in reader:
        if headers is None:
            headers = row.keys()
            missing_headers = set(required_headers) - set(headers)
            if len(missing_headers) > 0:
                errors.append('Missing column headers: %s' % ','.join(list(missing_headers)))
                break
        if not row['gene_label']:
            errors.append('row %d: no gene label' % row_count)
        elif db.session.query(GeneDescription).filter(
                and_(GeneDescription.species == species,
                     GeneDescription.sequence_name == row['gene_label'],
                     GeneDescription.species_subgroup == row['species_subgroup'],
                     ~GeneDescription.status.in_(['withdrawn', 'superceded']))).count() > 0:
            errors.append('row %d: a gene with the name %s and subgroup %s is already in the database' % (row_count, row['gene_label'], row['species_subgroup']))
        if row['functionality'] not in ['F', 'ORF', 'P']:
            errors.append('row %d: functionality must be F, ORF or P' % row_count)
        if row['type'][:3] not in ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG']:
            errors.append('row %d: locus in type must be one of %s' % (row_count, ','.join(['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG'])))
        if row['type'][3:] not in ['V', 'D', 'J', 'CH1', 'CH2', 'CH3', 'CH4', 'Leader']:
            errors.append('row %d: sequence_type in type must be one of %s' % (row_count, ','.join(['V', 'D', 'J', 'CH1', 'CH2', 'CH3', 'CH4', 'Leader'])))
        if not row['sequence']:
            errors.append('row %d: no sequence' % row_count)
        if not row['sequence_gapped']:
            errors.append('row %d: no sequence_gapped' % row_count)

        try:
            level = int(row['affirmation'])
            if level < 0 or level > 3:
                errors.append('row %d: affirmation level must be an integer between 0 and 3' % row_count)
        except:
            errors.append('row %d: affirmation level must be an integer between 0 and 3' % row_count)

        if len(errors) >= 5:
            errors.append('(Only showing first few errors)')
            break

        row_count += 1

    if len(errors) > 0:
        errors.append('Sequences not uploaded: please fix errors and try again')
        form.upload_file.errors = errors
        return render_template('sequence_new.html', form=form, species=species)

    fi.seek(0)
    reader = csv.DictReader(fi)
    for row in reader:
        gene_description = GeneDescription()
        gene_description.sequence_name = row['gene_label']
        gene_description.imgt_name = row['imgt']
        gene_description.alt_names = row['alt_names']
        gene_description.species = species
        gene_description.species_subgroup = row['species_subgroup']
        gene_description.species_subgroup_type = row['subgroup_type']
        gene_description.status = 'draft'
        gene_description.maintainer = current_user.name
        gene_description.lab_address = current_user.address
        gene_description.functionality = row['functionality']
        gene_description.inference_type = row['inference_type']
        gene_description.release_version = 1
        gene_description.affirmation_level = int(row['affirmation'])
        gene_description.inferred_extension = False
        gene_description.ext_3prime = None
        gene_description.start_3prime_ext = None
        gene_description.end_3prime_ext = None
        gene_description.ext_5prime = None
        gene_description.start_5prime_ext = None
        gene_description.end_5prime_ext = None
        gene_description.sequence = row['sequence']
        gene_description.locus = row['type'][0:3]
        gene_description.sequence_type = row['type'][3:]
        gene_description.coding_seq_imgt = row['sequence_gapped']

        notes = ['Imported to OGRDB with the following notes:']
        for field in row.keys():
            if field not in required_headers and len(row[field]):
                if field != 'notes':
                    notes.append('%s: %s' % (field, row[field]))
                else:
                    notes.append('%s' % row[field])

        if len(notes) > 1:
            gene_description.notes = '\r\n'.join(notes)

        db.session.add(gene_description)
        db.session.commit()
        gene_description.description_id = "A%05d" % gene_description.id
        db.session.commit()

    return redirect(url_for('sequences', sp=species))


@app.route('/get_sequences/<id>', methods=['GET'])
@login_required
def get_sequences(id):
    sub = check_sub_view(id)
    if sub is None:
        return ('')

    seqs = []
    for seq in sub.inferred_sequences:
        if seq.gene_descriptions.count() == 0:
            seqs.append((seq.id, "Gen: %s  |  Subj: %s  |  Seq: %s" % (seq.genotype_description.genotype_name, seq.genotype_description.genotype_subject_id, seq.sequence_details.sequence_id)))
        else:
            add = True
            for desc in seq.gene_descriptions:
                if desc.status in ['published', 'draft']:
                    add = False
                    break

            if add:
                seqs.append((seq.id, "Gen: %s  |  Subj: %s  |  Seq: %s" % (seq.genotype_description.genotype_name, seq.genotype_description.genotype_subject_id, seq.sequence_details.sequence_id)))

    return json.dumps(seqs)


@app.route('/seq_add_inference/<id>', methods=['GET', 'POST'])
@login_required
def seq_add_inference(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/')

    form = NewSequenceForm()
    subs = db.session.query(Submission).filter(Submission.species==seq.species).filter(Submission.submission_status.in_(['reviewing', 'complete', 'published'])).all()
    form.create.label.text = "Add"
    form.submission_id.choices = [('', 'Select Submission')] +  [(s.submission_id, '%s (%s)' % (s.submission_id, s.submitter_name)) for s in subs]
    form.sequence_name.choices = [(0, 'Select Sequence')]

    if request.method == 'POST':        # Don't use form validation because the selects are dynamically updated
        if form.cancel.data:
            return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

        try:
            if form.submission_id.data == '0' or form.submission_id.data == None or form.submission_id.data == 'None':
                form.submission_id.errors = ['Please select a submission.']
                raise ValidationError()

            if form.sequence_name.data == '0' or form.sequence_name.data == None or form.sequence_name.data == 'None':
                form.sequence_name.errors = ['Please select a sequence.']
                raise ValidationError()
        except ValidationError as e:
            return render_template('sequence_add.html', form=form, name=seq.sequence_name, id=id)

        sub = db.session.query(Submission).filter_by(submission_id = form.submission_id.data).one_or_none()
        if sub.species != seq.species or sub.submission_status not in ('reviewing', 'published', 'complete'):
            flash('Submission is for the wrong species, or still in draft.')
            return redirect('/')

        inferred_seq = db.session.query(InferredSequence).filter_by(id = int(form.sequence_name.data)).one_or_none()

        if inferred_seq is None or inferred_seq not in sub.inferred_sequences:
            flash('Inferred sequence cannot be found in that submission.')
            return redirect('/')

        seq.inferred_sequences.append(inferred_seq)
        copy_acknowledgements(inferred_seq, seq)

        db.session.commit()
        return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

    return render_template('sequence_add.html', form=form, name=seq.sequence_name, id=id)


@app.route('/seq_add_genomic/<id>', methods=['GET', 'POST'])
@login_required
def seq_add_genomic(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/')

    form = GenomicSupportForm()

    if request.method == 'POST':
        if form.validate():
            if 'cancel' in request.form:
                return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

            support = None
            append = True
            if request.form['support_id'] != "":
                for s in seq.genomic_accessions:
                    if s.id == int(request.form['support_id']):
                        support = s
                        append = False
                        break

            if support is None:
                support = GenomicSupport()

            save_GenomicSupport(db, support, form, False)

            if append:
                db.session.add(support)
                seq.genomic_accessions.append(support)

            db.session.commit()
            return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

    return render_template('sequence_add_genomic.html', form=form, name=seq.sequence_name, id=id, support_id="", action="Add")


@app.route('/seq_edit_genomic/<seq_id>/<support_id>', methods=['GET', 'POST'])
@login_required
def seq_edit_genomic(seq_id, support_id):
    seq = check_seq_edit(seq_id)
    if seq is None:
        return redirect('/')

    support = db.session.query(GenomicSupport).filter_by(id=support_id).one_or_none()
    if support is None:
        return redirect(url_for('edit_sequence', id=seq_id, _anchor='inf'))

    form = GenomicSupportForm()
    if request.method == 'GET':
        populate_GenomicSupport(db, support, form)
        return render_template('sequence_add_genomic.html', form=form, name=seq.sequence_name, id=seq_id, action="Save", support_id=support_id)

    # POST goes back to seq_add_genomic


@app.route('/sequence/<id>', methods=['GET'])
def sequence(id):
    seq = check_seq_view(id)
    if seq is None:
        return redirect('/')

    form = FlaskForm()
    tables = setup_sequence_view_tables(db, seq, current_user.has_role(seq.species))
    versions = db.session.query(GeneDescription).filter(GeneDescription.species == seq.species)\
        .filter(GeneDescription.description_id == seq.description_id)\
        .filter(GeneDescription.status.in_(['published', 'superceded']))\
        .all()
    tables['versions'] = setup_sequence_version_table(versions, None)
    del tables['versions']._cols['sequence']
    del tables['versions']._cols['coding_seq_imgt']
    return render_template('sequence_view.html', form=form, tables=tables, sequence_name=seq.sequence_name)





# Copy submitter and acknowledgements from sequence submission to gene_description


@app.route('/edit_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_sequence(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/')

    tables = setup_sequence_edit_tables(db, seq)
    desc_form = GeneDescriptionForm(obj=seq)
    notes_form = GeneDescriptionNotesForm(obj=seq)
    hidden_return_form = HiddenReturnForm()
    history_form = JournalEntryForm()
    form = AggregateForm(desc_form, notes_form, history_form, hidden_return_form, tables['ack'].form)

    if request.method == 'POST':
        form.sequence.data = "".join(form.sequence.data.split())
        form.coding_seq_imgt.data = "".join(form.coding_seq_imgt.data.split())

        # Clean out the extension fields if we are not using them, so they can't fail validation
        if not form.inferred_extension.data:
            for control in [form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext, form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext]:
                control.data = None

        form.validate()
        valid = True

        for field in form._fields:
            if len(form[field].errors) > 0:
                if field in history_form._fields and 'history_btn' not in request.form:
                    form[field].errors = []
                else:
                    valid = False

        if form.action.data == 'published':
            for inferred_sequence in seq.inferred_sequences:
                if inferred_sequence.submission.submission_status == 'draft':
                    inferred_sequence.submission.submission_status = 'published'
                    valid = False
                if inferred_sequence.submission.submission_status == 'withdrawn':
                    flash("Can't publish this sequence: submission %s is withdrawn." % inferred_sequence.submission.submission_id)
                    valid = False

        if valid:
            try:
                validation_result = process_table_updates({'ack': tables['ack']}, request, db)
                if not validation_result.valid:
                    raise ValidationError()

                if form.inferred_extension.data:
                    validate_ext(form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext)
                    validate_ext(form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext)
                    if not(form.ext_3prime.data or form.ext_5prime.data):
                        form.inferred_extension.errors.append('Please specify an extension at at least one end')
                        raise ValidationError()

                if 'notes_attachment' in request.files:
                    for file in form.notes_attachment.data:
                        if file.filename != '':
                            af = None
                            for at in seq.attached_files:
                                if at.filename == file.filename:
                                    af = at
                                    break
                            if af is None:
                                af = AttachedFile()
                            af.gene_description = seq
                            af.filename = file.filename
                            db.session.add(af)
                            db.session.commit()
                            dirname = attach_path + seq.description_id

                            try:
                                if not isdir(dirname):
                                    mkdir(dirname)
                                with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                                    fo.write(file.stream.read())
                            except:
                                info = sys.exc_info()
                                flash('Error saving attachment: %s' % (info[1]))
                                app.logger.error(format_exc())
                                return redirect(url_for('edit_submission', id=seq.id))

                seq.notes = form.notes.data      # this was left out of the form definition in the schema so it could go on its own tab

                rearranged = len(seq.inferred_sequences) > 0
                genomic = len(seq.genomic_accessions) > 0
                if rearranged and genomic:
                    seq.inference_type = 'Genomic and rearranged'
                elif rearranged:
                    seq.inference_type = 'Rearranged'
                elif genomic:
                    seq.inference_type = 'Genomic'

                save_GeneDescription(db, seq, form)

                if 'add_inference_btn' in request.form:
                    return redirect(url_for('seq_add_inference', id=id))

                if 'upload_btn' in request.form:
                    return redirect(url_for('edit_sequence', id=id, _anchor='note'))

                if 'add_genomic_btn' in request.form:
                    return redirect(url_for('seq_add_genomic', id=id))

                if form.action.data == 'published':
                    publish_sequence(seq, form.body.data, True)
                    flash('Sequence published')
                    return redirect(url_for('sequences', sp=seq.species))

            except ValidationError:
                return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, jump=validation_result.tag, version=seq.release_version, attachment=len(seq.attached_files) > 0)

            if validation_result.tag:
                return redirect(url_for('edit_sequence', id=id, _anchor=validation_result.tag))
            else:
                return redirect(url_for('sequences', sp=seq.species))

        else:
            for field in tables['ack'].form:
                if len(field.errors) > 0:
                    return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, jump='ack', version=seq.release_version, attachment=len(seq.attached_files) > 0)

    return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, version=seq.release_version, attachment=len(seq.attached_files) > 0)


def publish_sequence(seq, notes, email):
    old_seq = db.session.query(GeneDescription).filter_by(description_id=seq.description_id,
                                                          status='published').one_or_none()
    if old_seq:
        old_seq.status = 'superceded'
        old_seq.duplicate_sequences = list()
        seq.release_version = old_seq.release_version + 1
    else:
        seq.release_version = 1
    # Mark any referenced submissions as public
    for inferred_sequence in seq.inferred_sequences:
        sub = inferred_sequence.submission
        if not inferred_sequence.submission.public:
            inferred_sequence.submission.public = True
            db.session.commit()
            add_history(current_user, 'Submission published', sub, db)
            send_mail(
                'Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species),
                [sub.submitter_email], 'user_submission_published', reviewer=current_user, user_name=sub.submitter_name,
                submission=sub, sequence=seq)
            send_mail(
                'Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species),
                [sub.species], 'iarc_submission_published', reviewer=current_user, user_name=sub.submitter_name,
                submission=sub, sequence=seq)

        # Make a note in submission history if we haven't already
        title = 'Sequence %s listed in affirmation' % inferred_sequence.sequence_details.sequence_id
        entry = db.session.query(JournalEntry).filter_by(type='note', submission=sub, title=title).all()
        if not entry:
            add_note(current_user, title, safe_textile(
                '* Sequence: %s\n* Genotype: %s\n* Subject ID: %s\nis referenced in affirmation %s (sequence name %s)' %
                (inferred_sequence.sequence_details.sequence_id, inferred_sequence.genotype_description.genotype_name,
                 inferred_sequence.genotype_description.genotype_subject_id, seq.description_id, seq.sequence_name)),
                     sub, db)
    seq.release_date = datetime.date.today()
    add_history(current_user, 'Version %s published' % seq.release_version, seq, db, body=notes)

    if email:
        send_mail('Sequence %s version %d published by the IARC %s Committee' % (

    seq.description_id, seq.release_version, seq.species), [seq.species], 'iarc_sequence_released',
              reviewer=current_user, user_name=seq.maintainer, sequence=seq, comment=notes)
    seq.release_description = notes
    seq.status = 'published'
    db.session.commit()


@app.route('/download_sequence_attachment/<id>')
def download_sequence_attachment(id):
    att = check_seq_attachment_view(id)
    if att is None:
        return redirect('/')

    seq = att.gene_description

    try:
        dirname = attach_path + seq.description_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_sequence_attachment/<id>', methods=['POST'])
def delete_sequence_attachment(id):
    att = check_seq_attachment_edit(id)
    if att is None:
        return redirect('/')

    seq = att.gene_description

    try:
        dirname = attach_path + seq.description_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


@app.route('/delete_sequence/<id>', methods=['POST'])
@login_required
def delete_sequence(id):
    seq = check_seq_edit(id)
    if seq is not None:
        seq.delete_dependencies(db)
        db.session.delete(seq)
        db.session.commit()
    return ''


@app.route('/add_inferred_sequence', methods=['POST'])
@login_required
def add_inferred_sequence():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        inferred_seq = db.session.query(InferredSequence).filter(InferredSequence.id==request.form['inf']).one_or_none()
        if inferred_seq is not None and inferred_seq not in seq.inferred_sequences:
            seq.inferred_sequences.append(inferred_seq)
            copy_acknowledgements(inferred_seq, seq)
            db.session.commit()

    return ''


@app.route('/delete_inferred_sequence', methods=['POST'])
@login_required
def delete_inferred_sequence():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        inferred_seq = db.session.query(InferredSequence).filter(InferredSequence.id==request.form['inf']).one_or_none()
        if inferred_seq is not None and inferred_seq in seq.inferred_sequences:
            seq.inferred_sequences.remove(inferred_seq)
            db.session.commit()

    return ''


@app.route('/add_supporting_observation', methods=['POST'])
@login_required
def add_supporting_observation():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        genotype = db.session.query(Genotype).filter(Genotype.id==request.form['gid']).one_or_none()
        if genotype is not None and genotype not in seq.supporting_observations:
            seq.supporting_observations.append(genotype)
            copy_acknowledgements(genotype.genotype_description, seq)
            db.session.commit()

    return ''


@app.route('/delete_supporting_observation', methods=['POST'])
@login_required
def delete_supporting_observation():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        genotype = db.session.query(Genotype).filter(Genotype.id==request.form['gid']).one_or_none()
        if genotype is not None and genotype in seq.supporting_observations:
            seq.supporting_observations.remove(genotype)
            db.session.commit()

    return ''

@app.route('/delete_genomic_support', methods=['POST'])
@login_required
def delete_genomic_support():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        for ga in seq.genomic_accessions:
            if ga.id == int(request.form['gen']):
                seq.genomic_accessions.remove(ga)
                db.session.commit()

    return ''


@app.route('/draft_sequence/<id>', methods=['POST'])
@login_required
def draft_sequence(id):
    seq = check_seq_draft(id)
    if seq is not None:
        new_seq = GeneDescription()
        db.session.add(new_seq)
        db.session.commit()

        copy_GeneDescription(seq, new_seq)
        new_seq.description_id = seq.description_id
        new_seq.status = 'draft'

        for inferred_sequence in seq.inferred_sequences:
            new_seq.inferred_sequences.append(inferred_sequence)

        for gen in seq.supporting_observations:
            new_seq.supporting_observations.append(gen)

        for acc in seq.genomic_accessions:
            new_seq.genomic_accessions.append(acc)

        for journal_entry in seq.journal_entries:
            new_entry = JournalEntry()
            copy_JournalEntry(journal_entry, new_entry)
            new_seq.journal_entries.append(new_entry)

        db.session.commit()
    return ''

@app.route('/sequence_imgt_name', methods=['POST'])
@login_required
def sequence_imgt_name():
    if request.is_json:
        content = request.get_json()
        seq = check_seq_draft(content['id'])
        if seq is not None:
            seq.imgt_name = content['imgt_name']
            add_history(current_user, 'IMGT Name updated to %s' % seq.imgt_name, seq, db, body='IMGT Name updated.')
            send_mail('Sequence %s version %d: IMGT name updated to %s by the IARC %s Committee' % (seq.description_id, seq.release_version, seq.imgt_name, seq.species), [seq.species], 'iarc_sequence_released', reviewer=current_user, user_name=seq.maintainer, sequence=seq, comment='IMGT Name updated to %s' % seq.imgt_name)
            db.session.commit()
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
    return ''


@app.route('/withdraw_sequence/<id>', methods=['POST'])
@login_required
def withdraw_sequence(id):
    seq = check_seq_withdraw(id)
    if seq is not None:
        add_history(current_user, 'Published version %s withdrawn' % seq.release_version, seq, db, body = '')
        send_mail('Sequence %s version %d withdrawn by the IARC %s Committee' % (seq.description_id, seq.release_version, seq.species), [seq.species], 'iarc_sequence_withdrawn', reviewer=current_user, user_name=seq.maintainer, sequence=seq, comment='')
        seq.status = 'withdrawn'
        db.session.commit()
        seq.duplicate_sequences = list()
        flash('Sequence %s withdrawn' % seq.sequence_name)

        related_subs = []
        for inf in seq.inferred_sequences:
            related_subs.append(inf.submission)

        # un-publish any related submissions that now don't have published sequences

        published_seqs = db.session.query(GeneDescription).filter_by(species=seq.species, status='published').all()

        for related_sub in related_subs:
            other_published = False
            for ps in published_seqs:
                for inf in ps.inferred_sequences:
                    if inf.submission == related_sub:
                        other_published = True
                        break

            if not other_published:
                related_sub.submission_status = 'reviewing'
                related_sub.public = False
                add_history(current_user, 'Status changed from published to reviewing as submission %s was withdrawn.' % seq.description_id, related_sub, db, body = '')

        db.session.commit()

    return ''


@app.route('/add_sequence_dup_note/<seq_id>/<gen_id>/<text>', methods=['POST'])
@login_required
def add_sequence_dup_note(seq_id, gen_id, text):
    seq = check_seq_see_notes(seq_id)

    try:
        gen_id = int(gen_id)
    except:
        return('error')

    if seq is not None:
        gen = db.session.query(Genotype).filter_by(id = gen_id).one_or_none()
        if gen is not None and gen in seq.duplicate_sequences:
            for note in seq.dupe_notes:
                if note.genotype_id == gen_id:
                    db.session.delete(note)

        if len(text) > 0:
            note = DupeGeneNote(gene_description = seq, genotype = gen)
            note.author = current_user.name
            note.body = text
            note.date = datetime.datetime.now()
            db.session.add(note)

        db.session.commit()
    return ''

@app.route('/delete_sequence_dup_note/<seq_id>/<gen_id>', methods=['POST'])
@login_required
def delete_sequence_dup_note(seq_id, gen_id):
    try:
        gen_id = int(gen_id)
    except:
        return('error')

    seq = check_seq_see_notes(seq_id)
    if seq is not None:
        gen = db.session.query(Genotype).filter_by(id = gen_id).one_or_none()
        if gen is not None and gen in seq.duplicate_sequences:
            for note in seq.dupe_notes:
                if note.genotype_id == gen_id:
                    db.session.delete(note)
            db.session.commit()
    return ''


@app.route('/get_sequence_dup_note/<seq_id>/<gen_id>', methods=['POST'])
@login_required
def get_sequence_dup_note(seq_id, gen_id):
    try:
        gen_id = int(gen_id)
    except:
        return('error')

    seq = check_seq_see_notes(seq_id)
    if seq is not None:
        gen = db.session.query(Genotype).filter_by(id = gen_id).one_or_none()
        if gen is not None and gen in seq.duplicate_sequences:
            for note in seq.dupe_notes:
                if note.genotype_id == gen_id:
                    return json.dumps({'author': note.author, 'timestamp': note.date.strftime("%d/%m/%y %H:%M"), 'body': note.body})
        return ''
    else:
        return 'error'


@app.route('/download_sequences/<species>/<format>/<exc>')
def download_sequences(species, format, exc):
    if format not in ['gapped','ungapped','airr']:
        flash('Invalid format')
        return redirect('/')

    all_species = db.session.query(Committee.species).all()
    all_species = [s[0] for s in all_species]
    if species not in all_species:
        flash('Invalid species')
        return redirect('/')

    q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.affirmation_level != '0', GeneDescription.species == species)
    results = q.all()

    imgt_ref = get_imgt_reference_genes()
    if species in imgt_ref and exc == 'non':
        descs = []
        for result in results:
            if result.imgt_name == '':
                descs.append(result)
        results = descs

    if len(results) < 1:
        flash('No sequences to download')
        return redirect('/')

    if format == 'airr':
        ad = []
        for desc in results:
            ad.append(vars(AIRRAlleleDescription(desc)))

        dl = json.dumps(ad, default=str, indent=4)
        ext = 'json'
    else:
        dl = descs_to_fasta(results, format)
        ext = 'fa'

    filename = 'affirmed_germlines_%s_%s.%s' % (species, format, ext)
    return Response(dl, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})


@app.route('/genomic_support/<id>', methods=['GET'])
def genomic_support(id):
    genomic_support = db.session.query(GenomicSupport).filter(GenomicSupport.id == id).one_or_none()

    if genomic_support is None or not genomic_support.gene_description.can_see(current_user):
        return redirect('/')

    table = make_GenomicSupport_view(genomic_support, genomic_support.gene_description.can_edit(current_user))

    for item in table.items:
        if item['item'] == 'URL':
            item['value'] = Markup('<a href="%s">%s</a>' % (item['value'], item['value']))

    return render_template('genomic_support_view.html', table=table, name=genomic_support.gene_description.sequence_name)


@app.route('/sequence_from_vdjbase/<id>', methods=['GET', 'POST'])
@login_required
def sequence_from_vdjbase(id):
    novel_rec = db.session.query(NovelVdjbase).filter(NovelVdjbase.id == id).one_or_none()

    if not novel_rec:
        flash('VDJbase sequence not found')
        return redirect(url_for('vdjbase_review'))

    if not current_user.has_role(novel_rec.species):
        flash('You do not have rights to create the sequence')
        return redirect(url_for('vdjbase_review'))

    if db.session.query(GeneDescription).filter(and_(
            GeneDescription.species == novel_rec.species,
            GeneDescription.locus == novel_rec.locus,
            GeneDescription.sequence_name == novel_rec.vdjbase_name
            )).count():
        flash('A sequence with that name already exists in OGRDB')
        return redirect(url_for('vdjbase_review'))

    gene_description = GeneDescription()
    gene_description.sequence_name = novel_rec.vdjbase_name
    gene_description.species = novel_rec.species
    parse_name_to_gene_description(gene_description)
    gene_description.status = 'draft'
    gene_description.maintainer = current_user.name
    gene_description.lab_address = current_user.address
    gene_description.functionality = 'F'
    gene_description.inference_type = 'Rearranged Only'
    gene_description.release_version = 1
    gene_description.affirmation_level = 0
    gene_description.inferred_extension = False
    gene_description.ext_3prime = None
    gene_description.start_3prime_ext = None
    gene_description.end_3prime_ext = None
    gene_description.ext_5prime = None
    gene_description.start_5prime_ext = None
    gene_description.end_5prime_ext = None
    gene_description.sequence = novel_rec.sequence.replace('.', '')
    gene_description.locus = novel_rec.locus
    gene_description.coding_seq_imgt = novel_rec.sequence
    db.session.add(gene_description)
    db.session.commit()
    gene_description.description_id = "A%05d" % gene_description.id
    db.session.commit()

    if novel_rec.notes_entries:
        notes = ['Imported to OGRDB from VDJbase with the following notes:']
        notes.append(novel_rec.notes_entries[0].notes_text)
    else:
        notes = ['Imported to OGRDB from VDJbase']

    gene_description.notes = '\r\n'.join(notes)

    if novel_rec.notes_entries and novel_rec.notes_entries[0].attached_files:
        for vdjbase_af in novel_rec.notes_entries[0].attached_files:
            af = AttachedFile()
            af.gene_description = gene_description
            af.filename = vdjbase_af.filename
            db.session.add(af)
            db.session.commit()
            vdjbase_dirname = attach_path + 'V%5d' % novel_rec.id
            dirname = attach_path + gene_description.description_id

            try:
                if not isdir(dirname):
                    mkdir(dirname)
                vdjbase_fn = 'multi_attachment_%s' % vdjbase_af.id
                fn = 'multi_attachment_%s' % af.id
                full_path = os.path.join(dirname, fn)
                shutil.copyfile(os.path.join(vdjbase_dirname, vdjbase_fn), full_path)
            except:
                flash('Error saving attachment: %s' % vdjbase_af.filename)
                app.logger.error(format_exc())

    db.session.commit()
    return redirect(url_for('edit_sequence', id=gene_description.id))

