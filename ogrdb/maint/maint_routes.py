from flask import flash, redirect
from flask_login import login_required, current_user
from werkzeug.utils import redirect
from db.userdb import User
from db.submission_db import Submission
from receptor_utils import simple_bio_seq as simple


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


# Check that gene end coordinate is correct for all gene descriptions and fix where necessary
@app.route('/fix_gene_coords', methods=['GET'])
@login_required
def check_gene_end():
    if not current_user.has_role('Admin'):
        return redirect('/')

    # gene description

    descs = db.session.query(GeneDescription).all()

    for desc in descs:
        if desc.status in ['published', 'draft']:
            if desc.coding_seq_imgt is None or len(desc.coding_seq_imgt) == 0:
                print(f'No coding sequence for {desc.species} {desc.sequence_name}')
                continue
            if desc.gene_start is None:
                print(f'Gene start not set for {desc.species} {desc.sequence_name}')
                desc.gene_start = 1
            if desc.gene_end is None:
                print(f'Gene end not set for {desc.species} {desc.sequence_name}')
                desc.gene_start = 1
            coding_seq = desc.coding_seq_imgt.replace('.', '')
            pos = pos = desc.sequence.find(coding_seq)
            if pos == -1:
                print(f'Coding sequence not found for {desc.species} {desc.sequence_name}')
                # fix for IGHV-KAOG
                continue
            start_coord = pos + 1
            end_coord = pos + len(desc.coding_seq_imgt.replace('.', ''))
            if start_coord != desc.gene_start:
                print(f'Gene start incorrect for {desc.species} {desc.sequence_name} - {desc.gene_start} should be {start_coord}')
                desc.gene_start = start_coord
            if end_coord != desc.gene_end:
                print(f'Gene end incorrect for {desc.species} {desc.sequence_name} - {desc.gene_end} should be {end_coord}')
                desc.gene_end = end_coord

    db.session.commit()

    return 'Check complete'


from ogrdb.sequence.sequence_routes import delineate_v_gene

# Check trout seqs
@app.route('/check_trout', methods=['GET'])
@login_required
def check_trout():
    if not current_user.has_role('Admin'):
        return redirect('/')

    sp = "Oncorhynchus mykiss"
    #sp = "Homo sapiens"
    q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level != '0')
    results = q.all()

    '''
    for seq in sorted(results, key=lambda x: x.sequence_name):
        if 'V' in seq.sequence_type:
            for rec in seq.genomic_accessions:
                if rec.sense == 'reverse':
                    if rec.sequence_start > rec.sequence_end:
                        print('coords reversed')
                    else:
                        print('coords not reversed')
    '''

    accs = []
    assemblies = {}    
    for seq in sorted(results, key=lambda x: x.sequence_name):
        #if 'V' in seq.sequence_type:
        for rec in seq.genomic_accessions:
            if rec.accession not in accs:
                acc = rec.accession
                accs.append(acc)
                print(f'{seq.sequence_name} {rec.accession}')
                assemblies[acc + '_forward'] = simple.read_single_fasta(f'D:/Research/ogrdb_data/rainbow_trout/gapping/{acc}.fasta')
                assemblies[acc + '_reverse'] = simple.reverse_complement(simple.read_single_fasta(f'D:/Research/ogrdb_data/rainbow_trout/gapping/{acc}.fasta'))

            if rec.sense not in ['forward', 'reverse']:
                print(f'Bad sense {rec.sense} for {seq.sequence_name} {rec.accession}')
                continue

            notfound = False

            if rec.sense == 'forward':
                if rec.sequence != assemblies[rec.accession + '_forward'][rec.sequence_start-1:rec.sequence_end]:
                    print(f'Bad sequence coords for {seq.sequence_name} {rec.accession} {rec.sense} start:{rec.sequence_start} end:{rec.sequence_end}')
                    notfound = True
            else:
                s, e = rec.sequence_start, rec.sequence_end
                if rec.sequence_start > rec.sequence_end:
                    print(f'Reversed coords for  {seq.sequence_name} {rec.accession} {rec.sense} start:{rec.sequence_start} end:{rec.sequence_end}')
                    s, e = e, s
                if simple.reverse_complement(rec.sequence) != assemblies[rec.accession + '_forward'][s-1:e]:
                    print(f'Bad sequence coords for rc {seq.sequence_name} {rec.accession} {rec.sense} start:{s} end:{e}')
                    notfound = True

            if notfound:
                if rec.sequence in assemblies[rec.accession + '_forward']:
                    start = assemblies[rec.accession + '_forward'].index(rec.sequence) + 1
                    end = start + len(rec.sequence) - 1
                    print(f'Found in forward: start: {start} end: {end}')
                elif simple.reverse_complement(rec.sequence) in assemblies[rec.accession + '_forward']:
                    start = assemblies[rec.accession + '_forward'].index(simple.reverse_complement(rec.sequence)) + 1
                    end = start + len(rec.sequence) - 1
                    print(f'Found in reverse: start: {end} end: {start}')
                else:
                    print(f'Not found in assembly')
            #else:
                #print(f'Matched coords for {seq.sequence_name} {rec.accession} {rec.sense} start:{rec.sequence_start} end:{rec.sequence_end}') 


    return ret

