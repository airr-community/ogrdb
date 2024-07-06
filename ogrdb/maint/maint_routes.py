from flask import flash, redirect
from flask_login import login_required, current_user
from werkzeug.utils import redirect
from db.userdb import User
from db.submission_db import Submission


from db.gene_description_db import GeneDescription
from db.germline_set_db import GermlineSet
from db.submission_db import Submission
from db.novel_vdjbase_db import NovelVdjbase
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

    descs = db.session.query(Submission).all()

    for desc in descs:
        desc.duplicate_sequences = list()
        if desc.status in ['published', 'draft']:
            desc.build_duplicate_list(db, desc.sequence)

    db.session.commit()

    return 'Gene description links rebuilt'

import uuid


'''
@app.route('/add_uuid', methods=['GET'])
def add_uuid():
    #if not current_user.has_role('Admin'):
    #    return redirect('/')

    recs = db.session.query(User).all()
    for rec in recs:
        rec.fs_uniquifier = uuid.uuid4().hex
    db.session.commit()
    return 'Success'
'''


sp_to_binomial = {
    "human": "Homo sapiens",
    "human_tcr": "Homo sapiens",
    "mouse": "Mus musculus",
    "atlantic salmon": "Salmo salar",
    "salmon": "Salmo salar",
    "rainbow trout": "Oncorhynchus mykiss",
}


@app.route('/use_binomial', methods=['GET'])
@login_required
def add_use_binomial():
    if not current_user.has_role('Admin'):
        return redirect('/')

    recs = db.session.query(NovelVdjbase).all()
    for rec in recs:
        if rec.species.lower() in sp_to_binomial:
            rec.species = sp_to_binomial[rec.species.lower()]
        elif rec.species not in sp_to_binomial.values():
            print(f"unexpected species: {rec.species}")
    
    db.session.commit()
    return 'Success'


