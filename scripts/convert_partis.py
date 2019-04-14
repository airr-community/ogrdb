import yaml
import json
import argparse
import csv

parser = argparse.ArgumentParser(description="Parse partis data for OGRDB genotype file")
parser.add_argument('partis_yaml', help='.yaml file created by partis')
parser.add_argument('partis_tsv', help='.tsv file created by partis')
parser.add_argument('ogrdb_recs', help='annotation output file (.tsv)')
parser.add_argument('ogrdb_vs', help='v_gene sequences (.fasta)')
args = parser.parse_args()

with open(args.partis_yaml) as yamlfile:
    try:
        yamlfo = json.load(yamlfile)  # way tf faster than full yaml (only lost information is ordering in ordered dicts, but that's only per-gene support and germline info, neither of whose order we care much about)
    except ValueError:  # I wish i could think of a better way to do this, but I can't
        yamlfile.seek(0)
        yamlfo = yaml.load(yamlfile, Loader=yaml.CLoader)  # use this instead of the json version to make more human-readable files

with open(args.ogrdb_vs, 'w') as fastafile:
    for k, v in yamlfo['germline-info']['seqs']['v'].iteritems():
        fastafile.write('>%s\n%s\n' % (k, v))

tsv_recs = {}
found_cdr3s = False
for seq in yamlfo['events']:
    rec = {}
    rec['SEQUENCE_ID'] = seq['unique_ids'][0]
    if 'cdr3_seqs' in seq:
        rec['CDR3_IMGT'] = seq['cdr3_seqs'][0]
        found_cdr3s = True
    for attr in ['invalid']:
        if attr in seq:
            rec[attr] = seq[attr]

    for attr in ['in_frames', 'stops']:
        if attr in seq:
            rec[attr] = seq[attr][0]

    rec['V_CALL_GENOTYPED'] = seq.get('v_gene', '')
    rec['D_CALL'] = seq.get('d_gene', '')
    rec['J_CALL'] = seq.get('j_gene', '')
    rec['SEQUENCE'] = seq['input_seqs'][0]
    tsv_recs[rec['SEQUENCE_ID']] = rec

if not found_cdr3s:
    print("There were no CDR3 sequences in the yaml file. Did you forget the option '--extra-annotation-columns cdr3_seqs' ?")

with open(args.partis_tsv, 'r') as fi:
    reader = csv.DictReader(fi, delimiter='\t')
    for row in reader:
        if row['SEQUENCE_ID'] in tsv_recs:
            tsv_recs[row['SEQUENCE_ID']]['SEQUENCE_IMGT'] = row['SEQUENCE_IMGT']
        else:
            print('Warning: sequence %s found in .tsv but not in .yaml' % row['SEQUENCE_ID'])

invalid = []
for name, row in tsv_recs.iteritems():
    if row['V_CALL_GENOTYPED'] is None or row['V_CALL_GENOTYPED'] == '':
        invalid.append(name)

for name in invalid:
    del tsv_recs[name]

if len(invalid) > 0:
    print('%d records with no V-call were removed.' % len(invalid))

with open(args.ogrdb_recs, 'wb') as tsvo:
    fieldnames = ['SEQUENCE_ID', 'invalid', 'in_frames', 'stops', 'V_CALL_GENOTYPED', 'D_CALL', 'J_CALL', 'SEQUENCE', 'CDR3_IMGT', 'SEQUENCE_IMGT']
    writer = csv.DictWriter(tsvo, fieldnames = fieldnames, restval='', extrasaction='ignore', delimiter='\t')
    writer.writeheader()
    for name, row in tsv_recs.iteritems():
        if 'SEQUENCE_IMGT' not in row:
            print('Warning: sequence %s found in .yaml but not in .tsv' % name)
        writer.writerow(row)