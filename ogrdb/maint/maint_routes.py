from flask import flash, redirect
from flask_login import login_required, current_user
from werkzeug.utils import redirect
from db.userdb import User
from db.submission_db import Submission
from receptor_utils import simple_bio_seq as simple


from db.gene_description_db import GeneDescription, GenomicSupport
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


# Check that genomic_support gene_start and gene_end coords have been completed, fix where necessary
@app.route('/fix_gene_coords', methods=['GET'])
@login_required
def fix_genomic_support_coords():
    if not current_user.has_role('Admin'):
        return redirect('/')
    
    used_assemblies = simple.read_fasta('wanted_assemblies.fasta')

    # gene description

    recs = db.session.query(GenomicSupport).all()

    for rec in recs:
               
        if not rec.gene_description:
            continue
        '''
        # if rec.accession not in used_assemblies:
        #     used_assemblies.append(rec.accession)
        
        if not rec.sequence_start or not rec.sequence_end:
            print(f'Missing sequence coords for {rec.gene_description.sequence_type} gene {rec.gene_description.sequence_name} acc {rec.accession}')

            if not rec.sequence:
                if rec.accession in used_assemblies:
                    rec.sequence = used_assemblies[rec.accession]
                    print('Sequence loaded from fasta')
                else:
                    print('No assembly sequence available')
                    continue

            if len(rec.sequence) > 1000:
                print('Large sequence, not fixing')
            else:
                rec.sequence_start = 1
                rec.sequence_end = len(rec.sequence)
                print('Coordinates added')
        
        continue
        '''

        if rec.gene_start and rec.gene_end:
            continue

        if not rec.gene_description:
            continue

        if not rec.gene_description.coding_seq_imgt:
            print(f'No coding sequence for {rec.gene_description.sequence_type} gene {rec.gene_description.sequence_name} acc {rec.accession}')
            continue

        gd_sequence = rec.gene_description.coding_seq_imgt.replace('.', '')
        rc_sequence = simple.reverse_complement(gd_sequence)

        if gd_sequence in rec.sequence and (rec.sense == 'forward' or rc_sequence not in rec.sequence):
            rec.gene_start = rec.sequence.index(gd_sequence) + 1 + rec.sequence_start - 1
            rec.gene_end = rec.gene_start + len(gd_sequence) - 1
            if rec.sense != 'forward':
                print(f'Gene sequence found opposite sense {rec.gene_description.sequence_type} gene {rec.gene_description.sequence_name} acc {rec.accession} should be forward')
                rec.sense = 'forward'
            print('fixed')
        elif rc_sequence in rec.sequence and (rec.sense == 'reverse' or gd_sequence not in rec.sequence):
            rec.gene_start = rec.sequence.index(rc_sequence) + 1 + rec.sequence_start - 1
            rec.gene_end = rec.gene_start + len(rc_sequence) - 1
            if rec.sense != 'reverse':
                print(f'Gene sequence found opposite sense {rec.gene_description.sequence_type} gene {rec.gene_description.sequence_name} acc {rec.accession}')
                rec.sense = 'reverse'
            print('fixed')
        else:
            print(f'Gene sequence not found in genomic sequence for {rec.gene_description.sequence_type} gene {rec.gene_description.sequence_name} acc {rec.accession}')
            if '.' in rec.accession:
                rec.accession = rec.accession.split('.')[0]
            if rec.accession in used_assemblies:
                if gd_sequence in used_assemblies[rec.accession]:
                    print('Found in forward assembly')
                    rec.sequence_start = max(1, used_assemblies[rec.accession].index(gd_sequence) - 100)
                    rec.sequence_end = min(len(used_assemblies[rec.accession]), used_assemblies[rec.accession].index(gd_sequence) + len(gd_sequence) + 100)
                    rec.sequence = used_assemblies[rec.accession][rec.sequence_start-1:rec.sequence_end]
                    if gd_sequence not in rec.sequence:
                        breakpoint()
                    rec.gene_start = rec.sequence.index(gd_sequence) + 1 + rec.sequence_start - 1
                    rec.gene_end = rec.gene_start + len(gd_sequence) - 1
                    rec.d_rs_3_prime_end = None
                    rec.d_rs_3_prime_end = None
                    rec.d_rs_5_prime_start = None
                    rec.d_rs_5_prime_end = None
                    rec.leader_1_start = None
                    rec.leader_1_end = None
                    rec.leader_2_start = None
                    rec.leader_2_end = None
                    rec.sense = 'forward'
                elif rc_sequence in used_assemblies[rec.accession]:
                    print('Found in reverse assembly')
                    rec.sequence_start = max(1, used_assemblies[rec.accession].index(rc_sequence) - 100)
                    rec.sequence_end = min(len(used_assemblies[rec.accession]), used_assemblies[rec.accession].index(rc_sequence) + len(rc_sequence) + 100)
                    rec.sequence = used_assemblies[rec.accession][rec.sequence_start-1:rec.sequence_end]
                    rec.gene_start = rec.sequence.index(rc_sequence) + 1 + rec.sequence_start - 1
                    rec.gene_end = rec.gene_start + len(rc_sequence) - 1
                    rec.d_rs_3_prime_end = None
                    rec.d_rs_3_prime_end = None
                    rec.d_rs_5_prime_start = None
                    rec.d_rs_5_prime_end = None
                    rec.leader_1_start = None
                    rec.leader_1_end = None
                    rec.leader_2_start = None
                    rec.leader_2_end = None
                    rec.sense = 'reverse'
                else:
                    print('Not found in assembly')
                    continue
            else:
                print('No assembly sequence available')
                continue

        deduced_seq = rec.sequence[rec.gene_start - 1 - rec.sequence_start + 1: rec.gene_end - rec.sequence_start + 1]
        if rec.sense == 'reverse':
            deduced_seq = simple.reverse_complement(deduced_seq)

        if deduced_seq != gd_sequence:
            print(f'Fixed gene coords do not match coding sequence for {rec.gene_description.sequence_type} gene {rec.gene_description.sequence_name}: gene_start {rec.gene_start} gene_end {rec.gene_end} sequence_start {rec.sequence_start} sequence_end {rec.sequence_end}')
            print(f'  Deduced: {deduced_seq}')
            print(f'  Coding: {rec.gene_description.coding_seq_imgt.replace(".", "")}')

    # print(used_assemblies)

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

