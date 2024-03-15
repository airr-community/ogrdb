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

# add cdr coordinates to all v-sequence records

from ogrdb.germline_set.to_airr import delineate_v_gene

@app.route('/add_cdr_coords', methods=['GET'])
@login_required
def add_cdr_coords():
    if not current_user.has_role('Admin'):
        return redirect('/')

    seqs = db.session.query(GeneDescription).all()

    for seq in seqs:
        if seq.sequence_type == 'V' and seq.coding_seq_imgt and not seq.cdr1_start:
            coding_ungapped = seq.coding_seq_imgt.replace('.', '')
            coding_start = 0

            if seq.sequence:
                coding_start = seq.sequence.find(coding_ungapped)

                if coding_start < 0:
                    print(f'Coding sequence is not contained in the gene sequence for {seq.id} {seq.sequence_name}')
                    continue

            uc = delineate_v_gene(seq.coding_seq_imgt)
            seq.cdr1_start = uc['cdr1_start'] + coding_start if uc['cdr1_start'] else None
            seq.cdr1_end = uc['cdr1_end'] + coding_start if uc['cdr1_end'] else None
            seq.cdr2_start = uc['cdr2_start'] + coding_start if uc['cdr2_start'] else None
            seq.cdr2_end = uc['cdr2_end'] + coding_start if uc['cdr2_end'] else None
            seq.cdr3_start = uc['fwr3_end'] + 1 + coding_start if uc['fwr3_end'] else None
    
    db.session.commit()
    return 'Success'


