# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Check for new versions of the IMGR reference set, log changes and update the version used by Ogre


import argparse
from Bio import SeqIO
import yaml
import datetime
import sys
import urllib.request
import os
import glob


def read_reference(filename, species):
    records = {}

    for sp in species:
        records[sp] = {}

    for rec in SeqIO.parse(filename, 'fasta'):
        rd = rec.description.split('|')
        if rd[2] in species and rd[4] in ['V-REGION', 'D-REGION', 'J-REGION']:
            records[rd[2]][rd[1]] = rec.seq

    return records


def main(argv):
    parser = argparse.ArgumentParser(description='Compare two versions of the imgt reference sequences and write notes of differences.')
    parser.add_argument('cfgfile', help='configuration file (yaml)')
    args = parser.parse_args()

    with open(args.cfgfile, 'r') as fc:
        config = yaml.load(fc)

    # find the latest downloaded file
    file_list = glob.glob(config['file_dir'] + '/' + config['file_prefix'] + '*')
    oldfile = max(file_list, key=os.path.getctime)

    # download a new reference set from IMGT
    newfile = config['file_dir'] + '/' + config['file_prefix'] + datetime.date.today().strftime('_%Y_%m_%d') + '.fasta'
    with urllib.request.urlopen(config['file_url']) as response:
        with open(newfile, 'wb') as fo:
            fo.write(response.read())

    species = config['species']
    old_recs = read_reference(oldfile, species)
    new_recs = read_reference(newfile, species)

    changes = False

    with open(config['log_file'], 'a') as fl:
        for sp in species:
            for rec in old_recs[sp].keys():
                if rec not in new_recs[sp]:
                    fl.write('%s DROPPED %s %s\n' % (datetime.datetime.now().isoformat(timespec='minutes'), sp, rec))
                    changes = True
                elif old_recs[sp][rec] != new_recs[sp][rec]:
                    fl.write('%s CHANGED %s %s\n' % (datetime.datetime.now().isoformat(timespec='minutes'), sp, rec))
                    fl.write('old: %s\nnew: %s\n' % (old_recs[sp][rec], new_recs[sp][rec]))
                    changes = True
            for rec in new_recs[sp].keys():
                if rec not in old_recs[sp]:
                    fl.write('%s ADDED %s %s\n' % (datetime.datetime.now().isoformat(timespec='minutes'), sp, rec))
                    changes = True

        if changes:
            with open(config['ogre_file'], 'w') as fo, open(newfile, 'r') as fi:
                fo.write(fi.read())
            if config['ogre_touch'] != 'none':
                os.system('touch %s' % config['ogre_touch'])
            fl.write('%s OGRDB file %s updated\n' % (datetime.datetime.now().isoformat(timespec='minutes'), config['ogre_file']))
        else:
            fl.write('%s No changes detected.\n' % (datetime.datetime.now().isoformat(timespec='minutes')))
            os.remove(newfile)

if __name__ == "__main__":
    main(sys.argv)
