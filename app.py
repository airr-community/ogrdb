from flask import Flask, render_template, request, redirect, flash, url_for, Response
from flask_security import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required
from flask_mail import Mail, email_dispatched
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from wtforms import SubmitField, IntegerField
from flask_table import Table, Col, LinkCol
import logging.handlers
import datetime
import json
from copy import deepcopy
from Bio import SeqIO
import io
import textile


from get_pmid_details import get_pmid_details

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_pyfile('config.cfg')
app.config.from_pyfile('secret.cfg')

handler = logging.handlers.RotatingFileHandler('app.log', maxBytes=1024 * 1024)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

db = SQLAlchemy(app)

from textile_filter import *

mail = Mail(app)
from mail import log_mail, send_mail
email_dispatched.connect(log_mail)

from journal import *


from db.userdb import User
from db.submission_db import *
from db.submission_list_table import *
from db.repertoire_db import *
from db.inference_tool_db import *
from db.genotype_db import *
from db.genotype_description_db import *
from db.genotype_upload import *
from db.genotype_view_table import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *

admin = Admin(app, template_mode='bootstrap3')
from forms.useradmin import *
from forms.submission_form import *
from forms.repertoire_form import *
from forms.security import *
from forms.submission_edit_form import *
from forms.aggregate_form import *
from forms.cancel_form import *
from forms.submission_view_form import *
from forms.journal_entry_form import *


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

migrate = Migrate(app, db)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj = current_user)
    form.email = ''
    if request.method == 'POST':
        if form.validate():
            save_Profile(db, current_user, form)
            flash('Profile updated.')

    return render_template('profile.html', form=form, current_user=current_user, url='profile')

@app.route('/submissions', methods=['GET', 'POST'])
def submissions():
    tables = {}
    show_completed = False

    if current_user.is_authenticated:
        q = db.session.query(Submission).join(Submission.owner).filter(User.email==current_user.email)
        results = q.all()
        tables['mine'] = setup_submission_list_table(results, current_user)
        tables['mine'].table_id = 'mine'

        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp):
                if 'completed' in request.args and request.args['completed'] == 'yes':
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing', 'complete']))
                    show_completed = True
                else:
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing']))
                    show_completed = False
                results = q.all()

                if 'species' not in tables:
                    tables['species'] = {}
                tables['species'][sp] = setup_submission_list_table(results, current_user)
                tables['species'][sp].table_id = sp

    q = db.session.query(Submission).filter_by(submission_status='published')
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
        return render_template('submission_edit.html', form = form, id=id, tables=tables)

    missing_sequence_error = False
    validation_result = ValidationResult()
    try:
        if ('save_btn' in request.form or 'submit_btn' in request.form) and not form.validate():
            raise ValidationError()

        # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
        validation_result = process_table_updates(tables, request, db)
        if not validation_result.valid:
            raise ValidationError()

        if 'submit_btn' in request.form:
            # Check we have at least one inferred sequence
            if len(sub.inferred_sequences) == 0:
                missing_sequence_error = True
                validation_result.tag = 'inferred_sequence'
                raise ValidationError()

            sub.submission_status = 'reviewing'
            add_history(current_user, 'Submission submitted to IARC %s Committee for review' % sub.species, sub, db)
            send_mail('Submission %s submitted to IARC %s Committee for review' % (sub.submission_id, sub.species), [current_user.email], 'user_submission_submitted', user=current_user, submission=sub)
            send_mail('Submission %s submitted to IARC %s Committee for review' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_received', user=current_user, submission=sub)
            db.session.commit()
            flash('Submission %s has been submitted to IARC for review.' % id)
            return redirect(url_for('submissions'))

        save_Submission(db, sub, form, False)
        save_Repertoire(db, sub.repertoire[0], form, False)

        if validation_result.route:
            return redirect(url_for(validation_result.route, id = validation_result.id))
        if validation_result.tag:
            return redirect(url_for('edit_submission', id=id, _anchor=validation_result.tag))
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

        return render_template('submission_edit.html', form = form, id=id, tables=tables, jump = validation_result.tag, missing_sequence_error=missing_sequence_error)


@app.route('/delete_submission/<id>', methods=['GET', 'POST'])
@login_required
def delete_submission(id):
    sub = check_sub_edit(id)
    if sub is not None:
        sub.delete_dependencies(db)
        db.session.delete(sub)
        db.session.commit()
    return ''


@app.route('/submission/<id>', methods=['GET', 'POST'])
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not sub.can_see(current_user):
        flash('Submission not found')
        return redirect('/submissions')

    (form, tables) = setup_submission_view_forms_and_tables(sub, db, sub.can_see_private(current_user))

    if request.method == 'GET':
        return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=(current_user.has_role(sub.species) and sub.submission_status != 'draft'), id=id, jump="", status=sub.submission_status)
    else:
        if not current_user.has_role(sub.species):
            flash('Submission not found')
            return redirect('/submissions')
        if form.validate():
            if form.action.data == 'draft':
                add_note(current_user, form.title.data, textile.textile('Submission returned to Submitter with the following message:\r\n\r\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission returned to Submitter', sub, db)
                send_mail('Submission %s returned to you from the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_returned', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s returned to Submitter by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_returned', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'draft'
                db.session.commit()
                flash('Submission returned to Submitter')
                return redirect('/submissions')
            elif form.action.data == 'published':
                add_note(current_user, form.title.data, textile.textile('Submission published with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission published', sub, db)
                send_mail('Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_published', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_published', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'published'
                db.session.commit()
                flash('Submission published')
                return redirect('/submissions')
            elif form.action.data == 'complete':
                add_note(current_user, form.title.data, textile.textile('Submission completed with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission completed', sub, db)
                send_mail('Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_completed', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_completed', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'complete'
                db.session.commit()
                flash('Submission marked as complete')
                return redirect('/submissions')
            elif form.action.data == 'review':
                add_note(current_user, form.title.data, textile.textile('Submission returned to IARC Review with the following message to the Submitter:\n\n' + form.body.data), sub, db)
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
           return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=(current_user.has_role(sub.species) and sub.submission_status != 'draft'), id=id, jump='modal', button='#'+form.action.data, status=sub.submission_status)


@app.route('/upload_primers/<id>/<primer_type>', methods=['POST'])
@login_required
def upload_primer(id, primer_type):
    sub = check_sub_edit(id)
    rep_id = sub.repertoire[0].id
    if sub is None:
        return redirect('/submissions')

    if 'file' not in request.files:
        flash('Nothing uploaded.')
    else:
        content = io.StringIO(request.files['file'].read().decode("utf-8"))
        seq_count = 0

        for seq_record in SeqIO.parse(content, 'fasta'):
            seq_count += 1

            if primer_type == 'forward':
                p = ForwardPrimer()
                p.repertoire_id = rep_id
                p.fw_primer_name = seq_record.id
                p.fw_primer_seq = str(seq_record.seq)
            else:
                p = ReversePrimer()
                p.repertoire_id = rep_id
                p.rv_primer_name = seq_record.id
                p.rv_primer_seq = str(seq_record.seq)

            db.session.add(p)

        if seq_count > 0:
            flash('Added %d %s primer records' % (seq_count, primer_type))
            db.session.commit()
        else:
            flash('No valid FASTA records found in file.')

        return ''


def check_tool_edit(id):
    try:
        tool = db.session.query(InferenceTool).filter_by(id = id).one_or_none()
        if tool is None:
            flash('Record not found')
            return None
        elif not tool.submission.can_edit(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return tool

@app.route('/edit_tool/<id>', methods=['GET', 'POST'])
@login_required
def edit_tool(id):
    tool = check_tool_edit(id)
    if tool is None:
        return redirect('/')

    form = AggregateForm(InferenceToolForm(), CancelForm())

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=tool.submission.submission_id, _anchor= 'tools'))

        if form.validate():
            save_InferenceTool(db, tool, form, new=False)
            return redirect(url_for('edit_submission', id=tool.submission.submission_id, _anchor='tools'))
    else:
        populate_InferenceTool(db, tool, form)

    return render_template('inference_tool_edit.html', form=form, submission_id=tool.submission.submission_id, id=id)


# AJAX - delete tool and associated data
@app.route('/delete_tool/<id>', methods=['POST'])
@login_required
def delete_tool(id):
    tool = check_tool_edit(id)
    if tool is not None:
        tool.delete_dependencies(db)
        db.session.delete(tool)
        db.session.commit()
    return ''



def check_tool_view(id):
    try:
        tool = db.session.query(InferenceTool).filter_by(id = id).one_or_none()
        if tool is None:
            flash('Record not found')
            return None
        elif not tool.submission.can_see(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return tool


@app.route('/inference_tool/<id>', methods=['GET'])
def inference_tool(id):
    tool = check_tool_view(id)
    if tool is None:
        return redirect('/')

    table = make_InferenceTool_view(tool, tool.submission.can_edit(current_user))
    return render_template('inference_tool_view.html', table=table)


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

    form = AggregateForm(GenotypeDescriptionForm(), CancelForm())
    form.inference_tool_id.choices = [( str(tool.id), tool.tool_settings_name) for tool in desc.submission.inference_tools]

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))

        if form.validate():
            try:
                if form.genotype_name.data != desc.genotype_name and form.genotype_name.data in [d.genotype_name for d in desc.submission.genotype_descriptions]:
                    form.genotype_name.errors.append('There is already a genotype description with that name.')
                    raise ValidationError()
                if form.genotype_file.data:
                    form.genotype_filename.data = form.genotype_file.data.filename
                    save_GenotypeDescription(db, desc, form, new=False)
                    desc.genotype_file = form.genotype_file.data.read()
                    db.session.commit()
                    blob_to_genotype(desc, db)
                else:
                    save_GenotypeDescription(db, desc, form, new=False)

                return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))
            except ValidationError as e:
                return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)
    else:
        populate_GenotypeDescription(db, desc, form)

        if desc.inference_tool is not None:
            form.inference_tool_id.data = desc.inference_tool_id

    return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)


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


@app.route('/genotype/<id>')
def genotype(id):
    desc = check_genotype_description_view(id)
    if desc is None:
        return redirect('/')

    tables = {}
    tables['desc'] = make_GenotypeDescription_view(desc, False)
    tables['desc'].items.append({"item": "Tool/Settings", "value": desc.inference_tool.tool_settings_name, "tooltip": ""})
    tables['genotype'] = setup_gv_table(desc)
    return render_template('genotype_view.html', desc=desc, tables=tables, id=id)

@app.route('/download_genotype/<id>')
def download_genotype(id):
    desc = check_genotype_description_view(id)
    if desc is None:
        return redirect('/')

    foo = desc.genotype_file.decode("utf-8")
    return Response(desc.genotype_file.decode("utf-8"), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=%s" % desc.genotype_filename})

# AJAX - Return JSON structure listing sequence names and Genotype ids, given a GenotypeDesc id
@app.route('/get_genotype_seqnames/<id>', methods=['POST'])
@login_required
def get_genotype_seqnames(id):
    desc = check_genotype_description_edit(id)
    if desc is None:
        return []

    ret = []
    for g in desc.genotypes:
        ret.append({"id": g.id, "name": g.sequence_id})

    return json.dumps(ret)

# AJAX - delete genotype and associated data
@app.route('/delete_genotype/<id>', methods=['POST'])
@login_required
def delete_genotype(id):
    desc = check_genotype_description_edit(id)
    if desc is not None:
        desc.delete_dependencies(db)
        db.session.delete(desc)
        db.session.commit()
    return ''


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

@app.route('/edit_inferred_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_inferred_sequence(id):
    seq = check_inferred_sequence_edit(id)
    if seq is None:
        return redirect('/')

    if len(seq.submission.genotype_descriptions) < 1:
        flash('Please create at least one Genotype before editing inferred sequences.')
        return redirect(url_for('edit_submission', id=seq.submission.submission_id))

    form = AggregateForm(InferredSequenceForm(), CancelForm())
    form.genotype_id.choices = [(str(desc.id), desc.genotype_name) for desc in seq.submission.genotype_descriptions]
    if seq.genotype_description is not None:
        form.sequence_id.choices = [('', 'Select a sequence')] + [(str(genotype.id), genotype.sequence_id) for genotype in seq.genotype_description.genotypes]
    else:
        form.sequence_id.choices = [('', 'Select a sequence')] + [(str(genotype.id), genotype.sequence_id) for genotype in seq.submission.genotype_descriptions[0].genotypes]

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

        if form.validate():
            try:
                if form.sequence_id.data == '':
                    form.sequence_id.errors.append('Please select a sequence from the genotype. Upload data to the genotype if no sequences are listed.')
                    raise ValidationError()
                for sequence in seq.submission.inferred_sequences:
                    if sequence is not seq and str(sequence.sequence_id) == form.sequence_id.data and str(sequence.genotype_id) == form.genotype_id.data:
                        form.sequence_id.errors.append('That inferred sequence is already listed in the submission.')
                        raise ValidationError()
                save_InferredSequence(db, seq, form, new=False)
                return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor= 'inferred_sequence'))
            except ValidationError as e:
                return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id)
    else:
        populate_InferredSequence(db, seq, form)
        form.genotype_id.data = str(seq.genotype_id) if seq.genotype_id else ''
        form.sequence_id.data = str(seq.sequence_id) if seq.sequence_id else ''


    return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id)


@app.route('/render_page/<page>')
def render_page(page):
    return render_template('static/%s' % page)

