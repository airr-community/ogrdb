from flask import Flask, render_template, request, redirect, flash, url_for, Response
from flask_security import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required, logout_user
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from sqlalchemy import and_


import json
from Bio import SeqIO
import io



from get_pmid_details import get_pmid_details

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_pyfile('config.cfg')
app.config.from_pyfile('secret.cfg')
admin_obj = Admin(app, template_mode='bootstrap3')

db = SQLAlchemy(app)
# At the moment files are stored MEME encoded, so this needs to be at least 2 or 3 times max file size
#db.session.execute('SET @@GLOBAL.max_allowed_packet=134217728')

mail = Mail(app)
from mail import send_mail


from textile_filter import *
from journal import *
from db.userdb import User
from db.submission_db import *
from db.submission_list_table import *
from db.sequence_list_table import *
from db.repertoire_db import *
from db.inference_tool_db import *
from db.genotype_db import *
from db.genotype_description_db import *
from db.genotype_upload import *
from db.genotype_view_table import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *
from db.notes_entry_db import *
from db.gene_description_db import *
from db.inferred_sequence_table import *
from db.primer_set_db import *
from db.primer_db import *

from forms.useradmin import *
from forms.submission_form import *
from forms.repertoire_form import *
from forms.security import *
from forms.submission_edit_form import *
from forms.aggregate_form import *
from forms.cancel_form import *
from forms.submission_view_form import *
from forms.journal_entry_form import *
from forms.sequence_new_form import *
from forms.gene_description_form import *
from forms.gene_description_notes_form import *
from forms.sequence_view_form import *
from forms.primer_set_edit_form import *


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
migrate = Migrate(app, db)

security = Security(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

from custom_logging import init_logging

init_logging(app, mail)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Add the test role if we are in UAT

    if 'UAT' in app.config and app.config['UAT']:
        if not user_datastore.find_role('Test'):
            user_datastore.create_role(name = 'Test')
        tc = db.session.query(Committee).filter(Committee.species == 'Test').count()
        if tc < 1:
            test_ctee = Committee()
            test_ctee.species = 'Test'
            test_ctee.committee = 'Test Committee'
            db.session.add(test_ctee)
            db.session.commit()
        if current_user.is_authenticated and not current_user.has_role('Test'):
            user_datastore.add_role_to_user(current_user, 'Test')
            db.session.commit()

    return render_template('index.html', current_user=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj = current_user)
    form.email = ''
    if request.method == 'POST':
        if form.validate():
            if 'disable_btn' in request.form:
                current_user.active = False
                save_Profile(db, current_user, form)
                flash('Account disabled.')
                logout_user()
                return redirect('/')
            else:
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

        delegated_species = {}
        for sub in current_user.delegated_submissions:
            delegated_species[sub.species] = True

        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp) or sp in delegated_species:
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
        return render_template('submission_edit.html', form = form, id=id, tables=tables, attachment=sub.notes_entries[0].notes_attachment_filename is not None and len(sub.notes_entries[0].notes_attachment_filename) > 0)

    missing_sequence_error = False
    validation_result = ValidationResult()
    try:
        if ('save_btn' in request.form or 'submit_btn' in request.form):
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

        # We've gone too far off-piste to use form initialisation or process() to push field values into the object
        # The main problem is that not all object attributes are represented in the form, for example submission_id
        # if these were present as hidden fields, maybe we could use process()

        if ('save_btn' in request.form or 'submit_btn' in request.form):
            for (k, v) in request.form.items():
                if hasattr(sub, k):
                    setattr(sub, k, v)
                elif hasattr(sub.repertoire[0], k):
                    setattr(sub.repertoire[0], k, v)

            db.session.commit()

            if 'notes_attachment' in request.files:
                sub.notes_entries[0].notes_attachment = request.files['notes_attachment'].read()
                db.session.commit()
                sub.notes_entries[0].notes_attachment_filename = request.files['notes_attachment'].filename

            if 'notes_text' in request.form:
                sub.notes_entries[0].notes_text = request.form['notes_text'].encode('utf-8')

            db.session.commit()

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

@app.route('/download_submission_attachment/<id>')
def download_submission_attachment(id):
    sub = check_sub_view(id)
    if sub is None:
        return redirect('/')

    if len(sub.notes_entries[0].notes_attachment) > 0:
        return Response(sub.notes_entries[0].notes_attachment, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % sub.notes_entries[0].notes_attachment_filename})
    else:
        return redirect('/')

@app.route('/delete_submission_attachment/<id>', methods=['POST'])
def delete_submission_attachment(id):
    sub = check_sub_edit(id)
    if sub is None:
        return redirect('/')

    sub.notes_entries[0].notes_attachment = ''.encode('utf-8')
    sub.notes_entries[0].notes_attachment_filename = ''
    db.session.commit()
    return ''


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
    reviewer = (current_user.has_role(sub.species) or current_user in sub.delegates)
    if sub is None or not (sub.can_see(current_user) or current_user.has_role('Admin')):
        flash('Submission not found')
        return redirect('/submissions')

    (form, tables) = setup_submission_view_forms_and_tables(sub, db, sub.can_see_private(current_user))

    if request.method == 'GET':
        return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump="", status=sub.submission_status, attachment=sub.notes_entries[0].notes_attachment_filename is not None and len(sub.notes_entries[0].notes_attachment_filename) > 0)
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
                    for g in desc.genotypes:
                        db.session.delete(g)

                    blob_to_genotype(desc, db)
                else:
                    form.genotype_filename.data = desc.genotype_filename       # doesn't get passed back in request as the field is read-only
                    save_GenotypeDescription(db, desc, form, new=False)

                return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))
            except ValidationError as e:
                return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)
    else:
        populate_GenotypeDescription(db, desc, form)

        if desc.inference_tool is not None:
            form.inference_tool_id.data = str(desc.inference_tool_id)
            form.inference_tool_id.default = str(desc.inference_tool_id)

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

@app.route('/genotype_e/<id>')
def genotype_e(id):
    return genotype(id, True)

# 'editable' parameter indicates whether links back to the submission should be editable or not
@app.route('/genotype/<id>')
def genotype(id, editable=False):
    desc = check_genotype_description_view(id)
    sub = desc.submission
    reviewer = (current_user.has_role(sub.species) or current_user in sub.delegates)
    if desc is None:
        return redirect('/')

    tables = {}
    tables['desc'] = make_GenotypeDescription_view(desc, False)
    tables['desc'].items.append({"item": "Tool/Settings", "value": desc.inference_tool.tool_settings_name, "tooltip": ""})
    tables['genotype'] = setup_gv_table(desc)
    fasta = setup_gv_fasta(desc)
    submission_link = 'edit_submission' if editable else 'submission'
    return render_template('genotype_view.html', desc=desc, tables=tables, id=id, fasta=fasta, reviewer=reviewer, sub_id=sub.submission_id, submission_link=submission_link)

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

                if form.inferred_extension.data:
                    validate_ext(form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext)
                    validate_ext(form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext)
                    if not(form.ext_3prime.data or form.ext_5prime.data):
                        form.inferred_extension.errors.append('Please specify an extension at at least one end')
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

def check_seq_view(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
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

def check_seq_edit(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
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


@app.route('/sequences', methods=['GET', 'POST'])
def sequences():
    tables = {}
    show_withdrawn = False

    if current_user.is_authenticated:
        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp):
                if 'withdrawn' in request.args and request.args['withdrawn'] == 'yes':
                    q = db.session.query(GeneDescription).filter(GeneDescription.organism==sp).filter(GeneDescription.status.in_(['draft', 'withdrawn']))
                    show_withdrawn = True
                else:
                    q = db.session.query(GeneDescription).filter(GeneDescription.organism==sp).filter(GeneDescription.status.in_(['draft']))
                    show_withdrawn = False
                results = q.all()

                if 'species' not in tables:
                    tables['species'] = {}
                tables['species'][sp] = setup_sequence_list_table(results, current_user)
                tables['species'][sp].table_id = sp

    q = db.session.query(GeneDescription).filter_by(status='published')
    results = q.all()
    tables['affirmed'] = setup_sequence_list_table(results, current_user)
    tables['affirmed'].table_id = 'affirmed'

    return render_template('sequence_list.html', tables=tables, show_withdrawn=show_withdrawn)

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
            return redirect('/sequences')

        try:
            if form.new_name.data is None or len(form.new_name.data) < 1:
                form.new_name.errors = ['Name cannot be blank.']
                raise ValidationError()

            if db.session.query(GeneDescription).filter(and_(GeneDescription.organism == species, GeneDescription.sequence_name == form.new_name.data, ~GeneDescription.status.in_(['withdrawn', 'superceded']))).count() > 0:
                form.new_name.errors = ['A sequence already exists with that name.']
                raise ValidationError()

            if form.submission_id.data == '0' or form.submission_id.data == '' or form.submission_id.data == 'None':
                form.submission_id.errors = ['Please select a submission.']
                raise ValidationError()

            if form.sequence_name.data == '0' or form.sequence_name.data == '' or form.sequence_name.data == 'None':
                form.sequence_name.errors = ['Please select a sequence.']
                raise ValidationError()

            sub = db.session.query(Submission).filter_by(submission_id = form.submission_id.data).one_or_none()
            if sub.species != species or sub.submission_status == 'draft':
                return redirect('/sequences')

            seq = db.session.query(InferredSequence).filter_by(id = int(form.sequence_name.data)).one_or_none()

            if seq is None or seq not in sub.inferred_sequences:
                return redirect('/sequences')

            gene_description = GeneDescription()
            gene_description.sequence_name = form.new_name.data
            gene_description.inferred_sequences.append(seq)
            gene_description.sequence = seq.sequence_details.nt_sequence
            gene_description.organism = species
            gene_description.status = 'draft'
            gene_description.author = current_user.name
            gene_description.lab_address = current_user.address
            gene_description.functional = True
            gene_description.inference_type = 'Rearranged Only'
            gene_description.release_version = 1
            gene_description.affirmation_level = 0

            # Parse the name, if it's tractable

            try:
                sn = gene_description.sequence_name
                if sn[:2] == 'IG' or sn[:2] == 'TR':
                    ld = {'H': 'Heavy', 'K': 'Light-Kappa', 'L': 'Light-Lambda', 'A': 'Alpha', 'B': 'Beta', 'G': 'Gamma', 'D': 'Delta'}
                    gene_description.locus = ld[sn[2]]
                    gene_description.domain = sn[3]
                    if '-' in sn:
                        snp = sn.split('-')
                        gene_description.gene_subgroup = snp[0][4:]
                        if '*' in snp[1]:
                            snq = snp[1].split('*')
                            gene_description.subgroup_designation = snq[0]
                            gene_description.allele_designation = snq[1]
                        else:
                            gene_description.subgroup_designation = snp[1]
                    elif '*' in sn:
                        snq = sn.split('*')
                        gene_description.gene_subgroup = snq[0][4:]
                        gene_description.allele_designation = snq[1]
                    else:
                        gene_description.gene_subgroup = sn[4:]
            except:
                pass

            db.session.add(gene_description)
            db.session.commit()
            gene_description.description_id = "A%05d" % gene_description.id
            db.session.commit()
            return redirect('/sequences')

        except ValidationError as e:
            return render_template('sequence_new.html', form=form, species=species)


    return render_template('sequence_new.html', form=form, species=species)

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
        return redirect('/sequences')

    form = NewSequenceForm()
    subs = db.session.query(Submission).filter(Submission.species==seq.organism).filter(Submission.submission_status.in_(['reviewing', 'complete', 'published'])).all()
    form.create.label.text = "Add"
    form.submission_id.choices = [('', 'Select Submission')] +  [(s.submission_id, '%s (%s)' % (s.submission_id, s.submitter_name)) for s in subs]
    form.sequence_name.choices = [(0, 'Select Sequence')]

    if request.method == 'POST':        # Don't use form validation because the selects are dynamically updated
        if form.cancel.data:
            return redirect('/sequences')

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
        if sub.species != seq.organism or sub.submission_status == 'draft':
            flash('Submission is for the wrong species, or still in draft.')
            return redirect(url_for(sequences, id=id))

        inferred_seq = db.session.query(InferredSequence).filter_by(id = int(form.sequence_name.data)).one_or_none()

        if inferred_seq is None or inferred_seq not in sub.inferred_sequences:
            flash('Inferred sequence cannot be found in that submission.')
            return redirect(url_for(sequences, id=id))

        seq.inferred_sequences.append(inferred_seq)
        db.session.commit()
        return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

    return render_template('sequence_add.html', form=form, name=seq.sequence_name, id=id)


@app.route('/sequence/<id>', methods=['GET'])
def sequence(id):
    seq = check_seq_view(id)
    if seq is None:
        return redirect('/sequences')

    form = FlaskForm()
    tables = setup_sequence_view_tables(db, seq)
    return render_template('sequence_view.html', form=form, tables=tables, sequence_name=seq.sequence_name)


@app.route('/edit_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_sequence(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/sequences')

    tables = setup_sequence_edit_tables(db, seq)
    desc_form = GeneDescriptionForm(obj=seq)
    notes_form = GeneDescriptionNotesForm(obj=seq)
    hidden_return_form = HiddenReturnForm()
    history_form = JournalEntryForm()
    form = AggregateForm(desc_form, notes_form, history_form, hidden_return_form, tables['ack'].form)

    if request.method == 'POST':
        form.sequence.data = "".join(form.sequence.data.split())
        form.coding_seq_imgt.data = "".join(form.coding_seq_imgt.data.split())

        # Ignore journal validators, unless we are saving a journal entry

        form.validate()
        valid = True

        for field in form._fields:
            if len(form[field].errors) > 0:
                if field in history_form._fields and 'history_btn' not in request.form:
                    form[field].errors = []
                else:
                    valid = False

        if valid:
            try:
                validation_result = process_table_updates({'ack': tables['ack']}, request, db)
                if not validation_result.valid:
                    raise ValidationError()

                seq.notes = form.notes.data      # this was left out of the form definition in the schema so it could go on its own tab
                save_GeneDescription(db, seq, form)

                if 'add_inference_btn' in request.form:
                    return redirect(url_for('seq_add_inference', id=id))

                if form.action.data == 'published':
                    old_seq = db.session.query(GeneDescription).filter_by(description_id = seq.description_id, status='published').one_or_none()
                    if old_seq:
                        old_seq.status = 'superceded'
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
                            send_mail('Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_published', reviewer=current_user, user_name=sub.submitter_name, submission=sub, sequence=seq)
                            send_mail('Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_published', reviewer=current_user, user_name=sub.submitter_name, submission=sub, sequence=seq)

                        # Make a note in submission history if we haven't already
                        title = 'Sequence %s listed in affirmation' % inferred_sequence.sequence_details.sequence_id
                        entry = db.session.query(JournalEntry).filter_by(type = 'note', submission=sub, title=title).all()
                        if not entry:
                            add_note(current_user, title, safe_textile('* Sequence: %s\n* Genotype: %s\n* Subject ID: %s\nis referenced in affirmation %s (sequence name %s)' %
                                (inferred_sequence.sequence_details.sequence_id, inferred_sequence.genotype_description.genotype_name, inferred_sequence.genotype_description.genotype_subject_id, seq.description_id, seq.sequence_name)), sub, db)

                    seq.release_date = datetime.date.today()
                    add_history(current_user, 'Version %s published' % seq.release_version, seq, db, body = form.body.data)
                    send_mail('Sequence %s version %d published by the IARC %s Committee' % (seq.description_id, seq.release_version, seq.organism), [seq.organism], 'iarc_sequence_released', reviewer=current_user, user_name=seq.author, sequence=seq, comment=form.body.data)
                    seq.release_description = form.body.data
                    seq.status = 'published'
                    db.session.commit()
                    flash('Sequence published')
                    return redirect('/sequences')

            except ValidationError:
                return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, jump=validation_result.tag, version=seq.release_version)

            if validation_result.tag:
                return redirect(url_for('edit_sequence', id=id, _anchor=validation_result.tag))
            else:
                return redirect(url_for('sequences'))

        else:
            for field in tables['ack'].form:
                if len(field.errors) > 0:
                    return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, jump='ack', version=seq.release_version)

    return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, version=seq.release_version)


@app.route('/delete_sequence/<id>', methods=['POST'])
@login_required
def delete_sequence(id):
    seq = check_seq_edit(id)
    if seq is not None:
        seq.delete_dependencies(db)
        db.session.delete(seq)
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

        for journal_entry in seq.journal_entries:
            new_entry = JournalEntry()
            copy_JournalEntry(journal_entry, new_entry)
            new_seq.journal_entries.append(new_entry)

        db.session.commit()
    return ''


@app.route('/withdraw_sequence/<id>', methods=['POST'])
@login_required
def withdraw_sequence(id):
    seq = check_seq_draft(id)
    if seq is not None:
        seq.status = 'withdrawn'
        db.session.commit()
        flash('Sequence %s withdrawn' % seq.sequence_name)
    return ''

def check_primer_set_edit(id):
    try:
        set = db.session.query(PrimerSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

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

