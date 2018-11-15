# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Get publication details from PubMed

import requests
import argparse
import sys


def get_pmid_details(pmid):

    ret = {}

    try:
        i = int(pmid)
    except:
        raise ValueError('PubMed id must be an integer')

    try:
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&rettype=abstract&id=%s' % pmid)
        if r.status_code != 200:
            raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
        c = r.json()

        if 'error' in c['result'][pmid]:
            e = c['result'][pmid]['error']
            if 'cannot get document summary' in e:
                e = 'No document exists with pubMed id %s' % pmid
            raise ValueError(e)

        ret['title'] = c['result'][pmid]['title']

        authors  = []
        for author in c['result'][pmid]['authors']:
            authors.append(author['name'])

        ret['authors'] = ', '.join(authors)

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching PmID info from NIH: Exception %s with message %s' % (exc_type, exc_value))

    return ret


def main(argv):
    parser = argparse.ArgumentParser(description='Test harness for PMID fetcher')
    parser.add_argument('pmid', help='PMID')
    args = parser.parse_args()

    res = get_pmid_details(args.pmid)
    print('Title: %s, Authors: %s' % (res['title'], res['authors']))

if __name__=="__main__":
    main(sys.argv)

