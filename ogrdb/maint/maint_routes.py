from flask import flash, redirect
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from db.gene_description_db import GeneDescription
from db.submission_db import Submission
from head import app, db

# Unpublished route that will remove all sequences and submissions published by the selenium test account
@app.route('/remove_test', methods=['GET'])
@login_required
def remove_test():
    if not current_user.has_role('Admin'):
        return redirect('/')

    test_user = 'fred tester'

    seqs = db.session.query(GeneDescription).filter(GeneDescription.maintainer == test_user).all()
    for seq in seqs:
        seq.delete_dependencies(db)
        db.session.delete(seq)
    db.session.commit()

    subs = db.session.query(Submission).filter(Submission.submitter_name == test_user).all()
    for sub in subs:
        sub.delete_dependencies(db)
        db.session.delete(sub)
    db.session.commit()

    flash("Test records removed.")
    return redirect('/')

# Permanent maintenance route to rebuild duplicate links
@app.route('/rebuild_duplicates', methods=['GET'])
@login_required
def rebuild_duplicates():
    if not current_user.has_role('Admin'):
        return redirect('/')

    # gene description

    descs = db.session.query(GeneDescription).all()

    for desc in descs:
        desc.duplicate_sequences = list()
        if desc.status in ['published', 'draft']:
            desc.build_duplicate_list(db, desc.sequence)

    db.session.commit()

    return('Gene description links rebuilt')

# Remove 'No longer seen' entries from vdjbase notes as they were all added by a bug

from db.novel_vdjbase_db import NovelVdjbase

@app.route('/clean_notes', methods=['GET'])
@login_required
def clean_notes():
    if not current_user.has_role('Admin'):
        return redirect('/')

    vdjbase_entries = db.session.query(NovelVdjbase).all()

    for entry in vdjbase_entries:
        note_rows = entry.notes_entries[0].notes_text.split('\r')
        new_rows = []
        for row in note_rows:
            if 'No longer seen in VDJbase' not in row:
                new_rows.append(row)
        entry.notes_entries[0].notes_text = '\r'.join(new_rows)
        if entry.status == 'not current':
            entry.status = 'not reviewed'

    db.session.commit()
    return 'Success'


