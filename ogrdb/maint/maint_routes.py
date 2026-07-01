from flask import flash, redirect, Response
from flask_login import login_required, current_user
from werkzeug.utils import redirect
from markupsafe import escape
from db.userdb import User
from db.submission_db import Submission
from receptor_utils import simple_bio_seq as simple


from db.gene_description_db import GeneDescription, GenomicSupport
from db.germline_set_db import GermlineSet
from db.submission_db import Submission
from db.novel_vdjbase_db import NovelVdjbase
from head import app, db


STOP_CODONS = {'TAA', 'TAG', 'TGA'}
CYS_CODONS = {'TGT', 'TGC'}


def has_stop_before_aa(coding_seq, aa_limit):
    if not coding_seq:
        return False, None
    scan_len = min(len(coding_seq), aa_limit * 3)
    for i in range(0, scan_len - 2, 3):
        if coding_seq[i:i + 3] in STOP_CODONS:
            return True, (i // 3) + 1
    return False, None


def get_codon_at_aa(coding_seq, aa_pos):
    if not coding_seq:
        return None
    seq = coding_seq.upper()
    start = (aa_pos - 1) * 3
    end = start + 3
    if len(seq) < end:
        return None
    return seq[start:end]


def _norm_seq(value):
    if not value:
        return ''
    return ''.join(str(value).split()).upper()


def _aligned_to_ungapped_pos(aligned_seq, aligned_pos):
    if aligned_pos < 1 or aligned_pos > len(aligned_seq):
        return None
    if aligned_seq[aligned_pos - 1] == '.':
        return None
    return sum(1 for ch in aligned_seq[:aligned_pos] if ch != '.')

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


    return 'Check complete'


# List published mouse gene descriptions with functionality F and early stop codons
@app.route('/mouse_f_stop_104', methods=['GET'])
@login_required
def mouse_f_stop_104():
    if not current_user.has_role('Admin'):
        return redirect('/')

    species = 'Mus musculus'
    functionality = 'F'

    descs = db.session.query(GeneDescription).filter(
        GeneDescription.status == 'published',
        GeneDescription.species == species,
        GeneDescription.functionality == functionality
    ).all()

    results = []
    for desc in descs:
        has_stop, aa_pos = has_stop_before_aa(desc.coding_seq_imgt, 103)
        if not has_stop:
            continue
        results.append({
            'id': desc.id,
            'sequence_name': desc.sequence_name or '',
            'imgt_name': desc.imgt_name or '',
            'stop_aa': aa_pos
        })

    non_cys = []
    for desc in descs:
        codon = get_codon_at_aa(desc.coding_seq_imgt, 104)
        if not codon or codon in CYS_CODONS:
            continue
        non_cys.append({
            'id': desc.id,
            'sequence_name': desc.sequence_name or '',
            'imgt_name': desc.imgt_name or '',
            'codon_104': codon or 'N/A'
        })

    title = 'Published mouse gene_descriptions with functionality F and stop codon before aa 104'
    html_lines = [
        '<!doctype html>',
        '<html>',
        '<head>',
        f'<title>{escape(title)}</title>',
        '<style>',
        'body{font-family:Segoe UI,Arial,sans-serif;margin:24px;}',
        'table{border-collapse:collapse;width:100%;margin-top:12px;}',
        'th,td{border:1px solid #c8c8c8;padding:6px 8px;text-align:left;}',
        'th{background:#f2f2f2;}',
        '.meta{margin:8px 0 0 0;}',
        '</style>',
        '</head>',
        '<body>',
        f'<h2>{escape(title)}</h2>',
        f'<p class="meta"><strong>Total candidates:</strong> {len(descs)}</p>',
        f'<p class="meta"><strong>Total hits:</strong> {len(results)}</p>'
    ]

    if results:
        html_lines.extend([
            '<table>',
            '<thead>',
            '<tr>',
            '<th>ID</th>',
            '<th>Sequence Name</th>',
            '<th>IUIS Name</th>',
            '<th>Stop AA</th>',
            '</tr>',
            '</thead>',
            '<tbody>'
        ])
        for row in results:
            html_lines.append(
                '<tr>'
                f'<td>{escape(str(row["id"]))}</td>'
                f'<td>{escape(row["sequence_name"])}</td>'
                f'<td>{escape(row["imgt_name"])}</td>'
                f'<td>{escape(str(row["stop_aa"]))}</td>'
                '</tr>'
            )
        html_lines.extend(['</tbody>', '</table>'])
    else:
        html_lines.append('<p>No matches found.</p>')

    html_lines.extend([
        '<hr>',
        '<h3>Published mouse gene_descriptions without cysteine at aa 104</h3>',
        f'<p class="meta"><strong>Total candidates:</strong> {len(descs)}</p>',
        f'<p class="meta"><strong>Total hits:</strong> {len(non_cys)}</p>'
    ])

    if non_cys:
        html_lines.extend([
            '<table>',
            '<thead>',
            '<tr>',
            '<th>ID</th>',
            '<th>Sequence Name</th>',
            '<th>IUIS Name</th>',
            '<th>Codon 104</th>',
            '</tr>',
            '</thead>',
            '<tbody>'
        ])
        for row in non_cys:
            html_lines.append(
                '<tr>'
                f'<td>{escape(str(row["id"]))}</td>'
                f'<td>{escape(row["sequence_name"])}</td>'
                f'<td>{escape(row["imgt_name"])}</td>'
                f'<td>{escape(row["codon_104"])}</td>'
                '</tr>'
            )
        html_lines.extend(['</tbody>', '</table>'])
    else:
        html_lines.append('<p>No matches found.</p>')

    html_lines.extend(['</body>', '</html>'])
    return Response('\n'.join(html_lines), mimetype='text/html')


# Validate published mouse V-gene records for sequence and coordinate consistency
@app.route('/check_mouse_v_gene_descriptions', methods=['GET'])
@login_required
def check_mouse_v_gene_descriptions():
    if not current_user.has_role('Admin'):
        return redirect('/')

    species = 'Mus musculus'
    descs = db.session.query(GeneDescription).filter(
        GeneDescription.status == 'published',
        GeneDescription.species == species,
        GeneDescription.sequence_type.like('V%')
    ).all()

    cdr_spec = [
        ('cdr1_start', 79),
        ('cdr1_end', 114),
        ('cdr2_start', 166),
        ('cdr2_end', 195),
        ('cdr3_start', 313),
    ]

    exceptions = []

    for desc in sorted(descs, key=lambda x: (x.sequence_name or '', x.id)):
        print(desc.sequence_name)
        row_issues = []
        raw_coding = _norm_seq(desc.coding_seq_imgt)
        raw_sequence = _norm_seq(desc.sequence)
        ungapped_coding = raw_coding.replace('.', '')

        # 1) coding_seq_imgt (ungapped) should match sequence
        if ungapped_coding != raw_sequence:
            row_issues.append(
                f'check1: coding/sequence mismatch (ungapped coding {len(ungapped_coding)} bp, sequence {len(raw_sequence)} bp)'
            )

        # 2) sequence length implied by gene_start/gene_end should match sequence length
        if desc.gene_start is None or desc.gene_end is None:
            row_issues.append('check2: missing gene_start or gene_end')
        else:
            implied_len = (desc.gene_end - desc.gene_start) + 1
            if implied_len <= 0:
                row_issues.append(
                    f'check2: invalid gene span (gene_start={desc.gene_start}, gene_end={desc.gene_end})'
                )
            elif implied_len != len(raw_sequence):
                row_issues.append(
                    f'check2: implied length {implied_len} != sequence length {len(raw_sequence)}'
                )

        # 3) CDR coordinates should match unaligned positions from fixed aligned coordinates
        if not raw_coding:
            row_issues.append('check3: missing coding_seq_imgt')
        else:
            for field_name, aligned_pos in cdr_spec:
                actual_val = getattr(desc, field_name)
                expected_val = _aligned_to_ungapped_pos(raw_coding, aligned_pos)

                if actual_val is None:
                    row_issues.append(f'check3: {field_name} missing (expected {expected_val})')
                    continue

                if expected_val is None:
                    if field_name == 'cdr3_start' and aligned_pos == 313:
                        codon_positions = [310, 311, 312]
                        all_present = all(
                            pos <= len(raw_coding) and raw_coding[pos - 1] != '.'
                            for pos in codon_positions
                        )
                        if all_present:
                            codon_310_312 = ''.join(raw_coding[pos - 1] for pos in codon_positions)
                            if codon_310_312 != 'TGT':
                                row_issues.append('check3: second cysteine corrupted')
                        else:
                            row_issues.append('check3: sequence truncated before 2nd cysteine')
                    else:
                        row_issues.append(
                            f'check3: aligned position {aligned_pos} has no base in coding_seq_imgt for {field_name}'
                        )
                    continue

                if actual_val != expected_val:
                    row_issues.append(
                        f'check3: {field_name}={actual_val}, expected {expected_val} from aligned pos {aligned_pos}'
                    )

        if row_issues:
            exceptions.append({
                'id': desc.id,
                'sequence_name': desc.sequence_name or '',
                'imgt_name': desc.imgt_name or '',
                'issues': row_issues
            })

    title = 'Published mouse V gene_descriptions: sequence/coordinate checks'
    html_lines = [
        '<!doctype html>',
        '<html>',
        '<head>',
        f'<title>{escape(title)}</title>',
        '<style>',
        'body{font-family:Segoe UI,Arial,sans-serif;margin:24px;}',
        'table{border-collapse:collapse;width:100%;margin-top:12px;}',
        'th,td{border:1px solid #c8c8c8;padding:6px 8px;text-align:left;vertical-align:top;}',
        'th{background:#f2f2f2;}',
        '.meta{margin:8px 0 0 0;}',
        'ul{margin:0;padding-left:18px;}',
        '</style>',
        '</head>',
        '<body>',
        f'<h2>{escape(title)}</h2>',
        '<p class="meta">Checks: (1) sequence vs ungapped coding_seq_imgt, '
        '(2) gene_start/gene_end implied length vs sequence length, '
        '(3) CDR coords vs fixed aligned positions (cdr1 79-114, cdr2 166-195, cdr3 start 313).</p>',
        '<p class="meta">Coordinates are treated as 1-based.</p>',
        f'<p class="meta"><strong>Total records checked:</strong> {len(descs)}</p>',
        f'<p class="meta"><strong>Records with exceptions:</strong> {len(exceptions)}</p>'
    ]

    if exceptions:
        html_lines.extend([
            '<table>',
            '<thead>',
            '<tr>',
            '<th>ID</th>',
            '<th>Sequence Name</th>',
            '<th>IUIS Name</th>',
            '<th>Exceptions</th>',
            '</tr>',
            '</thead>',
            '<tbody>'
        ])
        for row in exceptions:
            issue_items = ''.join(f'<li>{escape(issue)}</li>' for issue in row['issues'])
            html_lines.append(
                '<tr>'
                f'<td>{escape(str(row["id"]))}</td>'
                f'<td>{escape(row["sequence_name"])}</td>'
                f'<td>{escape(row["imgt_name"])}</td>'
                f'<td><ul>{issue_items}</ul></td>'
                '</tr>'
            )
        html_lines.extend(['</tbody>', '</table>'])
    else:
        html_lines.append('<p>No exceptions found.</p>')

    html_lines.extend(['</body>', '</html>'])
    return Response('\n'.join(html_lines), mimetype='text/html')


