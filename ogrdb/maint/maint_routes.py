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

# Check/fix trout seqs
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


default_imgt_fr1 = (0, 87)
default_imgt_cdr1 = (87, 123)
default_imgt_fr2 = (123, 174)
default_imgt_cdr2 = (174, 210)
trout_imgt_fr3 = (210, 327)     # 2 codon insertion in FR3

# Fix all trout sequences, based on the defined sequence in the database
@app.route('/fix_trout', methods=['GET'])
@login_required
def fix_trout():
    if not current_user.has_role('Admin'):
        return redirect('/')

    sp = "Oncorhynchus mykiss"
    q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level != '0')
    results = q.all()
 
    assemblies = {}
    alignments = []

    for acc in ['NC_048583.1', 'NC_048589.1']:
        assemblies[acc] = simple.read_single_fasta(f'D:/Research/ogrdb_data/rainbow_trout/gapping/{acc}.fasta')

    for seq in sorted(results, key=lambda x: x.sequence_name):
        # fix sequence record
        # remove 5' nucleotide from Vs

        # specials
        if seq.sequence_name == 'TRB1V6_1':
            continue    # spliced V-gene: leave coords as they are
        elif seq.sequence_name == 'TRB2V13_18':
            seq.sequence = simple.reverse_complement(assemblies['NC_048589.1'][43341577:43341880])
            seq.coding_seq_imgt = 'CAGTTGTTTAGTAGCATGGTTCATCAGAGGCCTGTGGCACTAACAGAAGGACCTGGAGGAAACGTTCAACTCACCTGCAGCCATACGATCCCTAGC..................TACTACATGATACTATGGTACAAACAGTCAGCAGGAGACACTGCTATGAAACTCATTGGTTATGCATATACC......AAGTCAATAACCATGGAGAAATCATTTGAAAAGCACTTCAATGTGAGTGGAGACGGTGGG............AAAGAGGCTTATCTTCATCTAGTGAGTCTGAGAGGACCTGAACACAGTGCAGTTTATTACTGTGCAGCCAGCCAA'
        elif seq.sequence_name == 'TRB1V12_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'TTGGGTCTAGGTACCAGAGTTGTCCAGACTCCTGCTGCCTTGGTAATGACCCCAGGAGACTCCGCTGATCTCCACTGTTCTCACACTATAAAAGAC..................TATGATGTTATCCTCTGGTACAGACAGACTCATTCTCAGGACAGACAGCTACAACTGCTGGGGTACCTTTACACA......GACAACAAAAACCCAGAATCTCGTTTCAAGGACAAAATTAAATTGAGAGGAAACGCAGAA............CAGTATTGTGATTTAAGTGTTTCCAACCTGACACAAGAGGACAGTGCAGTGTATTTCTGTGCTGCCAGAGAG'
        elif seq.sequence_name == 'TRB1V7_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'TTCTATGACGATATAACAGTTAAACAGTCTCCTGTCCTGTCTGTGTGTAGAGAAGGAGATGCGTCAGTCACTCTACGGTGTTACCACGACGACAGCAGC..................TACTACTACATGTTCTGGTACCGACAGAGAGACAACAACATGGAGATGCTGACATATTCTCTGGGTCAAGGC......TTGTGGGAAATACAACCTCCCTTTGAGAAGGATGTACATTACACCATTAGCAGGCCGGAGCTG............ACTAGATCCACTCTGGAGATCAAGAACCTGGAGGTTGGGGACGGGGCTGTGTATTACTGTGCTTCCAGTACAG'
        elif seq.sequence_name == 'TRB1V7_2':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'TTCTATGACGGTATAACAGTTAAACAGTCTCCTGTCCTGTCTGTGTGTAGAGAAGGAGATGCGTCAGTCACTCTACGGTGTTACCACGACGACAGCAGC..................TACTACTACATGTTCTGGTACCGACAGAGAGACAACAACATGGAGATGCTGACATATTCTCTGGGTCAAGGC......TTGTGGGAAATACAACCTCCCTTTGAGAAGGATGTACATTACACCATGAGCAGGCCGGAGCTG............ACTAGATCCACTCTGGAGATCAAGAACCTGGAGGTTGGGGACGGGGCTGTGTATTACTGTGCTTCCAGTACAG'
        elif seq.sequence_name == 'TRB1V8_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'CATGTAAAGTGTGTTGCGTTTAGTCAGTCTCCGTCCCTGACAGTGAAGGACGGGCGCGAGGCGGAGATCCACTGTAGCCATGATGACAGTAAC.....................CTGTTGGTGATGTTGTGGTACCAACAGAGACAGGCCAGTATGACTCTGATCGGGTACAGTTACGGCACCACT.........GAGCCTAACTACGAGGGTTTGTTTGAGGAGAGGTTCAGGCAGAAGAGAGAGGGAAAC...............CTGAAGGGAACTCTCGTCATCTCCAAACTAACAGTAGCAGACTCTGCTGTGTACTTCTGCGCAGCCAGTCG'
        elif seq.sequence_name == 'TRB2V10_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGCTCTCTGAGCAGTAAAGTCCTCCAGGTTCCCTCAGCACTATTGGAAAGTCCCAATGTTACAGTGATAATCAAATGCAGCCACGCTATCAGTTCA..................TACAATACTATATTGTGGTACCAGCAGTCAATAGCTGATACTAATCTGAAACTGATTGGATTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGCTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCACAA'
        elif seq.sequence_name == 'TRB2V10_2':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGTTCTCTGAGCAGTAAAGTCCTCCAGGTTCCCTCAGCACTATTGGAAAGCCCCAATGTTACAGTGATAATCAAATGCAGCCATGCTATCAGTTCA..................TACAATACTATATTGTGGTACCAGCAGTCAATAGCTGATTCTAATCTGAAACTGATTGGATTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGCTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCACAA'
        elif seq.sequence_name == 'TRB2V7_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'TGTGACGGTATAACAGTTAAACAGTCTCCTGTCCTGTCCGTGTGTAGAGAAGGAGATGCGTCAGTCACTCTACGGTGTTACCACGACGACAGCAGC..................TACTACTACATGTTCTGGTACCGACAGAGAGACAACAACATGGAGATGCTGACATATTCTCAGGGTCAAGGCTTG......TGGGAAATACAACCTCCCTTTGAGAAGGATGTACATTACACCATGAGCAGGCCGGAGCTG............ACTAGATCCACTCTGGAGATCAAGAACTTGGAGGTTGGGGACGGGGCTGTGTATTACTGTGCTTCCAGTACAG'
        elif seq.sequence_name == 'TRB2V9_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'TCCTGTGTGTCCCTATCCGTCCAACAATCTCCTCGTCATCTCACCAAGAGGCCAGGAAACACCTTAAAGATGACCTGCAGTCACCATGACAGAAAC..................TATGATAAGATCTACTGGTACCGTCAGACAGATGGACAAAAGCTCCAGCTCATCGGCTTCCTGTCC..................TTTAAACAAGCTTTAGATGTTGCGGAAAACTTTAACATCTCAGGCGACGCAGAG...............GATGAGGGTTTTCTGGGGTCGCTTGCAGTGAGGGTTGAAGACACTGGGCTATATTATTGTGCTGTGAGTAAAG'
        elif seq.sequence_name == 'TRB3V10_1':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGTTCTCTGAGCAGTAAAGTCCTCCAGGTTCCCTCAGCACTATTGGAAAGTCCCAATGTTACAGTGATAATCAAATGCAGCCATACTCTCAGTTCA..................TACTATACTATATTGTGGTACCAGCAGTCAATAGCTGATACTAATCTGAAACTGATTGGAGTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGTTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCCAA'
        elif seq.sequence_name == 'TRB3V10_2':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGTTCTCTGAGCAGTAAAGTCCTCCAGGTTCCCTCAGCACTATTGGAAAGTCCCAATGTTACAGTGATAATCAAATGCAGCCATACTCTCAGTTCA..................TACTATACTATATTGTGGTACCAGCAGTCAATAGCTGATACTAATCTGAAACTGATTGGAGTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGTTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCCAA'
        elif seq.sequence_name == 'TRB3V10_3':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGTTCTCTGAGCAGTAAAGTCCTCCAGGTTCCCTCAGCACTATTGGAAAGTCCCAATGTTACAGTGATAATCAAATGCAGCCATACTCTCAGTTCA..................TACTATACTATATTGTGGTACCAGCAGTCAATAGCTGATACTAATCTGAAACTGATTGGAGTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGTTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCCAA'
        elif seq.sequence_name == 'TRB3V10_4':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGTTCTCTGAGCAGTAAAGTCCTCCAGGTTCCCTCAGCACTATTGGAAAGTCCCAATGTTACAGTGATAATCAAATGCAGCCATACTCTCAGTTCA..................TACTATACTATATTGTGGTACCAGCAGTCAATAGCTGATACTAATCTGAAACTGATTGGAGTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGTTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCCAA'
        elif seq.sequence_name == 'TRB3V10_5':
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'AGTTCTCTGGGCAGTAAAGTCTTCCAGGTTCCCTCAGCACTATTGGAAAGTCCCAATGTTACAGTGATAATCAAATGCAGCCATACTCTCAGTTCA..................TACTATACTATATTGTGGTACCAGCAGTCAATAGCTGATACTAATCTGAAACTGATTGGAGTTGTGTTTTAT......AAGAATCCAACAATTGAAGATCAATTCAAACAGCACTTTGAAATCCGTGGAGATGGAGAG............ATAGAAGCCTCACTTCAGCTT......CTGTCAGACCCTGAAAACAGTGCAGTGTATTACTGTGCAGCCAGCCAA'
        elif seq.sequence_name == 'TRB3V4_1':
            seq.sequence = seq.sequence[8:]
            seq.coding_seq_imgt = 'CTCAGTAAGGTAGTGTACCAGTCTCCCTCTACACTGCTGGTAGAGCCTAATGCGTCTGTCTCTGTCCCACTCAGCTCATAAAATCCC...................................................TAACTATGAGGGCTCTGAAACTCATAGCATATGTATACTATACAGGTC.......AGACTGTTGAACCCTCATATAAAGGTTACTTTGACGTGAAAGGTGAT......GGAAGGAACGAA............GCCTTCCTTCATCTCCTCAAACTGAGACAAGTTGAAGACAGTGGGGAGTATTTCTGTGCTGCTAGTTATA'
        elif seq.sequence_name == 'TRB3V4_2':
            seq.sequence = seq.sequence[8:]
            seq.coding_seq_imgt = 'CTCAGTAAGGTAGTGTACCAGTCTCCCTCTACACTGCTGGTAGAGCCTAATGCGTCTGTCTCTGTCCCACTCAGCTGCAGTCATAAAATCTCTAAC..................TATGACACTATCCTCTGGTACCAGCGTCCTGTGGGAGACACAGCTCTGAAACTCATAGCATATGTGTACTTT......ACAGGTCAGACTGTTGAACCCTCATATAAAGGTTACGTTGACGTGAAAGGTGATGGAAGG............AACGAAGCCTTCCTTCATCTCCTCAAACTGAGACAAGTTGAAGACAGTGGGGAGTATTTCTGTGCTGCTAGTTATA'
        elif seq.sequence_name == 'TRB3V7-1':
            seq.sequence_name = 'TRB3V7-1S'    # rename as in Pierre's mail 3/11/2024
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = 'TCCTCTCTCCTCATCCGCCAGACTCCTCAACACCTCCTGAGGAGGACAACTGAACACAGAGAGGCACACCTGGACTGTCACCACGGCGACAAGGAC..................TACCCATACATGTTGTGGTACCAACAGAAGGACAAGGGAGGACAGAAGACCATGGTACTCATTGGGACACTA......CACTATACAAACCCAACTCTTGAGAAGAACTATGAAACACGGTTCAACTTAACAGGGGATTCC......AAGGCCAAAGCCAGCCTGGTTAACTCTGAGATAAACCCT...ACAGACAGTGCAGTGTATTACTGTGCAGCCAGTCAG'
        elif 'V' in seq.sequence_type:
            seq.sequence = seq.sequence[2:]
            seq.coding_seq_imgt = seq.coding_seq_imgt[2:]

        seq.gene_start = 1
        seq.gene_end = len(seq.sequence)

        if seq.sequence != seq.coding_seq_imgt.replace('.', ''):
            print(f'{seq.sequence_name} gapped/ungapped sequence mismatch')
            print(f'{seq.sequence}')
            print(f'{seq.coding_seq_imgt}')

        if seq.sequence_name in ['TRB1V2_4', 'TRB1V7_1', 'TRB1V7_2', 'TRB2V10_1', 'TRB2V10_2', 'TRB2V13_23', 'TRB2V1_21', 'TRB2V1_26', 'TRB2V1_9', 'TRB2V2_1', 'TRB2V2_31', 'TRB2V3_2', 'TRB2V3_35', 'TRB3V4_1', 'TRB3V5_1']:
            seq.functionality = 'P'
        else:
            seq.functionality = 'F'

        if 'V' in seq.sequence_type:
            if seq.sequence_name not in ['TRB1V7_1', 'TRB1V7_2']:
                coords = delineate_v_gene(seq.coding_seq_imgt, [default_imgt_fr1, default_imgt_cdr1, default_imgt_fr2, default_imgt_cdr2, trout_imgt_fr3])
                seq.cdr1_start = coords['cdr1_start']
                seq.cdr1_end = coords['cdr1_end']
                seq.cdr2_start = coords['cdr2_start']
                seq.cdr2_end = coords['cdr2_end']
                seq.cdr3_start = coords['cdr3_start']
            else:
                coords = delineate_v_gene(seq.coding_seq_imgt, [(0, 90), (90, 126), (126, 177), (177, 213), (213, 330)])
                seq.cdr1_start = coords['cdr1_start']
                seq.cdr1_end = coords['cdr1_end']
                seq.cdr2_start = coords['cdr2_start']
                seq.cdr2_end = coords['cdr2_end']
                seq.cdr3_start = coords['cdr3_start']

            #print(f'{seq.sequence_name.ljust(20)} {simple.translate(seq.coding_seq_imgt)}')
            #print(seq.sequence)
            alignments.append(f'{seq.sequence_name.ljust(20)} {simple.translate(seq.coding_seq_imgt)} {simple.translate(seq.sequence[seq.cdr1_start-1:seq.cdr1_end])}  {simple.translate(seq.sequence[seq.cdr2_start-1:seq.cdr2_end])}  {simple.translate(seq.sequence[seq.cdr3_start-1:])}')

        # check evidence
        for rec in seq.genomic_accessions:
            # remove 5' nucleotide from Vs

            rec.sequence = seq.sequence

            if 'V' in seq.sequence_type:
                if rec.sequence in assemblies[rec.accession]:
                    rec.sequence = rec.sequence[1:]
                elif simple.reverse_complement(rec.sequence) in assemblies[rec.accession]:
                    rec.sequence = rec.sequence[:-1]
                else:
                    print(f'{seq.sequence_name} Not found in assembly, even after corrections')
            
            start = None
            end = None
            sense = None
            rec.sequence = seq.sequence

            if rec.sequence in assemblies[rec.accession]:
                start = assemblies[rec.accession].index(rec.sequence) + 1
                end = start + len(rec.sequence) - 1
                sense = 'forward'
                #print(f'{seq.sequence_name} Found in forward: start: {start} end: {end}')
            elif simple.reverse_complement(rec.sequence) in assemblies[rec.accession]:
                start = assemblies[rec.accession].index(simple.reverse_complement(rec.sequence)) + 1
                end = start + len(rec.sequence) - 1
                sense = 'reverse'
                #print(f'{seq.sequence_name} Found in reverse: start: {end} end: {start}')
            else:
                print(f'{seq.sequence_name} Not found in assembly')

            if start is not None:
                rec.sequence_start = start
                rec.sequence_end = end
                rec.sense = sense


    for al in alignments:
        print(al)

    db.session.commit()

    return ""

