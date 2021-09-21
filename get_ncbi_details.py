# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Get publication details from PubMed


import requests
import argparse
import sys
import re
import html
import time
from app import ncbi_api_key

# Requests to NCBI are limited to 10 per second. There's a sleep before each call to limit request rate
# Still no guarantee that we won't hit rate limiting if multiple users make requests at the same time


def get_pmid_details(pmid):
    ret = {}

    try:
        i = int(pmid)
    except:
        raise ValueError('PubMed id must be an integer')

    try:
        time.sleep(0.11)
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?api_key=%s&db=pubmed&retmode=json&rettype=abstract&id=%s' % (ncbi_api_key, pmid))
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
        raise ValueError('Error fetching PmID info from NIH: %s' % (exc_value))

    return ret


def get_nih_project_details(prj_id):
    ret = {}

    if len(prj_id) < 5 or (prj_id[:3] != 'SRP' and prj_id[:5] != 'PRJNA' and prj_id[:5] != 'PRJEB'):
        raise ValueError('bady formatted project id: %s' % (prj_id))

    try:
        if prj_id[:5] != 'PRJNA':
            time.sleep(0.11)
            foo = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?api_key=%s&db=sra&retmode=json&term=%s' % (ncbi_api_key, prj_id)
            r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?api_key=%s&db=sra&retmode=json&term=%s' % (ncbi_api_key, prj_id))
            if r.status_code != 200:
                raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
            c = r.json()

            if len(c['esearchresult']['idlist']) == 0:
                e = 'No project found in NCBI SRA with accession number %s' % prj_id
                raise ValueError(e)

            id = c['esearchresult']['idlist'][0]
            time.sleep(0.11)
            r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?api_key=%s&db=sra&retmode=json&rettype=abstract&id=%s' % (ncbi_api_key, id))

            if r.status_code != 200:
                raise ValueError('Unexpected response from NCBI: status %d' % r.status_code)
            c = r.json()

            if 'error' in c or id not in c['result']:
                e = 'No details could be retrieved for project with id %s' % id
                raise ValueError(e)

            xml = html.unescape(c['result'][id]['expxml'])
            exp = re.compile('Title.*?>(?P<title>.*?)<')
            m = exp.search(xml)
            ret['title'] = m.group('title')
            ret['url'] = 'https://www.ncbi.nlm.nih.gov/sra/?term=%s' % prj_id
        else:
            id = prj_id[5:]
            time.sleep(0.11)
            r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?api_key=%s&db=bioproject&retmode=json&rettype=abstract&id=%s' % (ncbi_api_key, id))

            if r.status_code != 200:
                raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
            c = r.json()

            if 'error' in c or id not in c['result']:
                e = 'No details could be retrieved for project id %s' % id
                raise ValueError(e)

            ret['title'] = c['result'][id]['project_title']
            ret['url'] = 'https://www.ncbi.nlm.nih.gov/bioproject/%s' % prj_id


    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching project info from NCBI: %s' % (exc_value))

    return ret


def get_nih_nuc_details(nuc_id):
    ret = {}

    try:
        time.sleep(0.11)
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?api_key=%s&db=nuccore&retmode=json&rettype=abstract&id=%s' % (ncbi_api_key, nuc_id))
        if r.status_code != 200:
            raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
        c = r.json()

        if 'error' in c:
            e = c['error']
            if 'Invalid uid' in e:
                e = 'No sequence in NIH nucleotide repository with id %s' % nuc_id
            raise ValueError(e)


        for uid in c['result']['uids']:
            if c['result'][uid]['caption'] == nuc_id:
                ret['title'] = c['result'][uid]['title']
                ret['caption'] = c['result'][uid]['caption']
                ret['url'] = 'https://www.ncbi.nlm.nih.gov/nuccore/%s' % nuc_id
                break

        if 'title' not in ret:
            e = 'No sequence in NIH nucleotide repository with id %s' % nuc_id
            raise ValueError(e)

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching nucleotide info from NIH: %s' % (exc_value))

    return ret


def get_nih_srr_details(srr_id):
    ret = {}

    if len(srr_id) < 5 or (srr_id[:3] != 'SRR' and srr_id[:3] != 'ERR'):
        raise ValueError('badly formatted SRR record accession number: %s' % (srr_id))

    try:
        time.sleep(0.11)
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?api_key=%s&db=sra&retmode=json&term=%s[accn]' % (ncbi_api_key, srr_id))
        if r.status_code != 200:
            raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
        c = r.json()

        if len(c['esearchresult']['idlist']) == 0 or len(c['esearchresult']['idlist']) > 1:
            e = 'No record set found in NCBI SRA with accession number %s' % srr_id
            raise ValueError(e)

        id = c['esearchresult']['idlist'][0]
        time.sleep(0.11)
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?api_key=%s&db=sra&retmode=json&rettype=abstract&id=%s' % (ncbi_api_key, id))
        if r.status_code != 200:
            raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
        c = r.json()

        if 'error' in c or id not in c['result']:
            e = 'No details could be retrieved for project with sra if %s' % id
            raise ValueError(e)

        xml = html.unescape(c['result'][id]['expxml'])
        exp = re.compile('Title.*?>(?P<title>.*?)<')
        m = exp.search(xml)
        ret['title'] = m.group('title')
        ret['url'] = 'https://trace.ncbi.nlm.nih.gov/Traces/sra/?run=' + srr_id


    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching nucleotide info from NIH: %s' % (exc_value))

    return ret

def get_nih_samn_details(sam_id):
    ret = {}

    if len(sam_id) < 5 or (sam_id[:4] != 'SAMN' and sam_id[:4] != 'SAME'):
        raise ValueError('badly formatted sample record accession number: %s' % (sam_id))

    try:
        time.sleep(0.11)
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?api_key=%s&db=biosample&retmode=json&term=%s[accn]' % (ncbi_api_key, sam_id))
        if r.status_code != 200:
            raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
        c = r.json()

        if len(c['esearchresult']['idlist']) == 0 or len(c['esearchresult']['idlist']) > 1:
            e = 'No record set found in NCBI SRA with accession number %s' % sam_id
            raise ValueError(e)

        id = c['esearchresult']['idlist'][0]
        time.sleep(0.11)
        r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?api_key=%s&db=biosample&retmode=json&rettype=abstract&id=%s' % (ncbi_api_key, id))
        if r.status_code != 200:
            raise ValueError('Unexpected response from NIH: status %d' % r.status_code)
        c = r.json()

        if 'error' in c or id not in c['result']:
            e = 'No details could be retrieved for project with sra if %s' % id
            raise ValueError(e)

        xml = html.unescape(c['result'][id]['sampledata'])
        exp = re.compile('Id db_label="Sample name">(?P<title>.*?)<')
        m = exp.search(xml)

        if m is not None:
            ret['title'] = m.group('title')
        else:
            ret['title'] = c['result'][id]['title']

        ret['url'] = 'https://www.ncbi.nlm.nih.gov/biosample/=' + sam_id


    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching nucleotide info from NIH: %s' % (exc_value))

    return ret


def main(argv):
    parser = argparse.ArgumentParser(description='Test harness for PMID fetcher')
    parser.add_argument('nuc_id', help='nuc_id')
    args = parser.parse_args()

    try:
        res = get_nih_samn_details(args.nuc_id)
    except Exception as e:
        pass

    print('Title: %s, Authors: %s' % (res['title'], res['authors']))

if __name__=="__main__":
    main(sys.argv)

