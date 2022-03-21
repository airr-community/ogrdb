# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Create a new submission or add to an existing submission from a VDJbase entry

import datetime
import os
import shutil
import sys
import requests
from os import mkdir, remove
from os.path import isdir
from traceback import format_exc

from flask import request, render_template, redirect, flash, Response, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_

from db.attached_file_db import AttachedFile
from db.genotype_description_db import GenotypeDescription
from db.inference_tool_db import InferenceTool
from db.inferred_sequence_db import InferredSequence
from db.journal_entry_db import JournalEntry
from db.notes_entry_db import NotesEntry
from db.novel_vdjbase_db import NovelVdjbase
from db.repertoire_db import Repertoire
from db.submission_db import Submission, save_Submission, populate_Submission
from db.vdjbase import get_vdjbase_sample_details, VDJbaseError, call_vdjbase
from forms.vdjbase_submission_form import VdjbaseSubmissionForm
from head import app, db, attach_path
from ogrdb.submission.genotype_upload import file_to_genotype


def get_accession_number(acc):
    if ' ' in acc:
        acc = acc.split(' ')[-1]
    return acc


def setup_form(novel_rec, sample_details):
    form = VdjbaseSubmissionForm()
    form.sample_name.data = novel_rec.example
    acc = get_accession_number(sample_details['study_acc_id'])

    form.submission_id.data = ''
    if acc:
        subs = db.session.query(Submission.submission_id).join(Repertoire).filter(and_(Repertoire.rep_accession_no == acc, Submission.submission_status == 'draft')).all()
        if subs:
            form.submission_id.data = subs[0][0]

    return form


@app.route('/submission_from_vdjbase/<id>', methods=['GET', 'POST'])
@login_required
def submission_from_vdjbase(id):
    novel_rec = db.session.query(NovelVdjbase).filter(NovelVdjbase.id == id).one_or_none()

    if not novel_rec:
        flash('VDJbase sequence not found')
        return redirect(url_for('vdjbase_review'))

    if not current_user.has_role(novel_rec.species):
        flash('You do not have rights to create the submission')
        return redirect(url_for('vdjbase_review'))

    try:
        sample_details = get_vdjbase_sample_details(novel_rec.species, novel_rec.locus, novel_rec.example)
    except Exception as e:
        flash(f'{e}')
        return redirect(url_for('vdjbase_review'))

    if request.method == 'POST':
        form = VdjbaseSubmissionForm(formdata=request.form)
        if 'cancel' in request.values:
            return redirect(url_for('vdjbase_review'))

        if form.validate():
            if form.sample_name.data != novel_rec.example:
                try:
                    sample_details = get_vdjbase_sample_details(novel_rec.species, novel_rec.locus, form.sample_name.data)
                except Exception as e:
                    form.sample_name.errors = ['Sample name not found in VDJbase']
                    return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)

            if not sample_details:
                form.sample_name.errors = ['Sample name not found in VDJbase']
                return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)

            if form.submission_id.data:
                sub = db.session.query(Submission).filter(Submission.submission_id == form.submission_id.data).one_or_none()
                if not sub:
                    form.submission_id.errors = ['Submission not found in OGRDB']
                    return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)
                if sub.submission_status != 'draft':
                    form.submission_id.errors = ['Submission must be in draft!']
                    return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)
                if sub.repertoire[0].rep_accession_no != get_accession_number(sample_details['study_acc_id']):
                    form.submission_id.errors = ['The submission accession number does not match this sequence']
                    return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)
                if novel_rec.vdjbase_name.upper() in [inf.sequence_details.sequence_id.upper() for inf in sub.inferred_sequences]:
                    form.submission_id.errors = [f'The inferred sequence {novel_rec.vdjbase_name} is already listed in the submission']
                    return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)

            else:
                sub = create_submission(sample_details, novel_rec.species)  # create submission, repertoire, inference tool

            copy_notes_to_submission(novel_rec, sub)
            tool = add_inference_tool(sub, sample_details)
            desc = add_genotype_description(sub, sample_details, tool, novel_rec.species, novel_rec.locus)
            add_inferred_sequence(desc, sub, sample_details, novel_rec.vdjbase_name)

            return redirect(url_for('edit_submission', id=sub.submission_id))

    form = setup_form(novel_rec, sample_details)
    return render_template('submission_from_vdjbase.html', form=form, sequence_name=novel_rec.vdjbase_name, id=id)


# set up submission, repertoire

def create_submission(sample_details, species):
    sub = Submission()
    sub.submission_date = datetime.date.today()
    sub.submission_status = 'draft'
    sub.submitter_name = current_user.name
    sub.submitter_address = current_user.address
    sub.submitter_email = current_user.email
    sub.species = species
    sub.population_ethnicity = 'UN'
    sub.owner = current_user
    sub.notes_entries.append(NotesEntry())
    db.session.commit()
    sub.submission_id = "S%05d" % sub.id

    rep = Repertoire()
    rep.rep_accession_no = get_accession_number(sample_details['study_acc_id'])
    rep.rep_title = ''
    rep.repository_name = ''
    rep.dataset_url = sample_details['study_acc_ref']
    if 'ncbi' in rep.dataset_url:
        rep.repository_name = 'NCBI SRA'
    elif 'ena' in rep.dataset_url:
        rep.repository_name = 'ENA'
    rep.miairr_compliant = 'N'
    rep.miairr_link = ''
    rep.sequencing_platform = sample_details['seq_platform']
    rep.read_length = sample_details['sequencing_length']
    rep.primers_overlapping = ''
    rep.submission = sub
    db.session.commit()
    return sub


# Copy notes and attachments from the novel_vdjbase record to the submission

def copy_notes_to_submission(novel_rec, sub):
    notes = []
    if sub.notes_entries[0].notes_text:
        notes.append(sub.notes_entries[0].notes_text)

    if novel_rec.notes_entries:
        notes.append(f'{novel_rec.vdjbase_name} imported to OGRDB from VDJbase with the following notes:')
        notes.append(novel_rec.notes_entries[0].notes_text)
    else:
        notes = ['{novel_rec.vdjbase_name} imported to OGRDB from VDJbase']

    sub.notes_entries[0].notes_text = '\r'.join(notes)

    if novel_rec.notes_entries:
        for vdjbase_af in novel_rec.notes_entries[0].attached_files:
            filename = vdjbase_af.filename

            af = None
            for at in sub.notes_entries[0].attached_files:
                if at.filename == filename:
                    af = at
                    break

            if af:
                continue

            af = AttachedFile()
            af.filename = filename
            sub.notes_entries[0].attached_files.append(af)
            db.session.commit()

            sub_dirname = attach_path + sub.submission_id
            sub_filename = 'multi_attachment_%s' % af.id
            vdjbase_dirname = attach_path + 'V%5d' % novel_rec.id
            vdjbase_filename = 'multi_attachment_%s' % vdjbase_af.id

            try:
                if not isdir(sub_dirname):
                    mkdir(sub_dirname)
                shutil.copyfile(os.path.join(vdjbase_dirname, vdjbase_filename), os.path.join(sub_dirname, sub_filename))
            except:
                info = sys.exc_info()
                flash('Error saving attachment: %s' % (info[1]))
                app.logger.error(format_exc())



# Add an inference tool record unless one exists

def add_inference_tool(sub, sample_details):
    if sub.inference_tools:
        return sub.inference_tools[0]
    tool = InferenceTool()
    tool.tool_settings_name = sample_details['sequencing_protocol']
    tool.tool_name = sample_details['geno_tool']
    tool.tool_version = sample_details['geno_ver']
    tool.tool_starting_database = sample_details['aligner_reference']
    tool.tool_settings = []

    for field in ['pipeline_name', 'prepro_tool', 'aligner_tool', 'aligner_ver',
                  'aligner_reference', 'geno_tool', 'geno_ver', 'haplotype_tool', 'haplotype_ver', 'single_assignment', 'detection']:
        tool.tool_settings.append(f'{field}: {sample_details[field]}')

    tool.tool_settings = '\r'.join(tool.tool_settings)

    sub.inference_tools.append(tool)
    db.session.commit()
    return tool

def add_genotype_description(sub, sample_details, tool, species, locus):
    vdjbase_species = species.replace('_TCR', '')
    gen_path = f"{app.config['VDJBASE_DOWNLOAD_PATH']}/{vdjbase_species}/{sample_details['chain']}/{sample_details['genotype_stats'].replace('samples/', '')}"
    try:
        contents = requests.get(gen_path)
    except Exception as e:
        flash(f'Genotype not loaded: {e}')
        return

    genotype_filename = sample_details['genotype_stats'].split('/')[-1]
    genotype_name = genotype_filename.replace('.csv', '')
    for gd in sub.genotype_descriptions:
        if gd.genotype_name == genotype_name:
            return          # genotype already in submission

    desc = GenotypeDescription()
    desc.genotype_name = genotype_name
    desc.genotype_filename = genotype_filename
    desc.genotype_subject_id = sample_details['name_in_paper']
    desc.locus = locus
    desc.sequence_type = 'V'
    sub.genotype_descriptions.append(desc)
    tool.genotype_descriptions.append(desc)
    db.session.commit()

    filename = 'genotype_%s.csv' % desc.id
    dirname = attach_path + sub.submission_id

    try:
        if not isdir(dirname):
            mkdir(dirname)
        with open(os.path.join(dirname, filename), 'w') as fo:
            fo.write(contents.text)
    except:
        info = sys.exc_info()
        flash('Error saving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    file_to_genotype(os.path.join(dirname, filename), desc, db)

    # now download ogrdbstats report as a multi-attachment

    gen_path = f"{app.config['VDJBASE_DOWNLOAD_PATH']}/{vdjbase_species}/{sample_details['chain']}/{sample_details['genotype_report'].replace('samples/', '')}"
    try:
        contents = requests.get(gen_path)
    except Exception as e:
        flash(f'OGRDBstats report not loaded: {e}')
        return desc

    af = AttachedFile()
    af.filename = sample_details['genotype_report'].split('/')[-1]
    sub.notes_entries[0].attached_files.append(af)
    db.session.commit()

    dirname = attach_path + sub.submission_id
    filename = 'multi_attachment_%s' % af.id

    try:
        with open(os.path.join(dirname, filename), 'wb') as fo:
            contents.raw.decode_content = True
            fo.write(contents.content)
    except:
        flash('Error saving OGRDBstats report')
        app.logger.error(format_exc())

    return desc

def add_inferred_sequence(desc, sub, sample_details, sequence_name):
    gen = None
    for gen in desc.genotypes:
        if gen.sequence_id.upper() == sequence_name.upper():
            break

    if not gen or gen.sequence_id.upper() != sequence_name.upper():
        flash('A sequence with that name was not found in the genotype')
        return

    seq = InferredSequence()
    seq.seq_accession_no = ''
    seq.seq_record_title = ''
    seq.deposited_version = ''
    seq.run_ids = ''
    seq.inferred_extension = False
    gen.inferred_sequences.append(seq)
    sub.inferred_sequences.append(seq)
    desc.inferred_sequences.append(seq)
    db.session.commit()

