# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Get accession detains from ENA


import requests
import argparse
import sys
import re
import html
import time
import xml.etree.ElementTree as ET


def get_ena_project_details(prj_id):
    ret = {}

    if len(prj_id) < 5 or (prj_id[:5] != 'PRJEB'):
        raise ValueError('bady formatted project id: %s' % (prj_id))

    try:
        r = requests.get('https://www.ebi.ac.uk/ena/browser/api/xml/%s' % prj_id)

        if r.status_code != 200:
            raise ValueError('Unexpected response from ENA: status %d' % r.status_code)
        foo = r.content.decode("utf-8")
        root = ET.fromstring(r.content)
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching project info from ENA: %s' % (exc_value))

    titles = root.findall("./PROJECT/TITLE")

    if len(titles) > 0:
        ret['title'] = titles[0].text if len(titles) > 0 else ''
        ret['url'] = 'https://www.ebi.ac.uk/ena/browser/api/xml/%s' % prj_id
    else:
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (root.text))

    return ret


def get_ena_nuc_details(nuc_id):
    ret = {}

    if len(nuc_id) < 5:
        raise ValueError('badly formatted nucleotide sequence record accession number: %s' % (nuc_id))

    try:
        title = ''
        request = 'https://www.ebi.ac.uk/ena/browser/api/xml/%s' % nuc_id
        r = requests.get(request)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            entries = root.findall("./entry/description")
            title = entries[0].text
        else:
            request = 'https://www.ebi.ac.uk/ena/browser/api/embl/%s' % nuc_id
            r = requests.get(request)
            if r.status_code == 200:
                lines = r.content.decode('utf-8')
                lines = lines.split('\n')
                for line in lines:
                    if line[:4] == 'DE  ':
                        title += line[4:]
            else:
                raise ValueError('Unexpected response from ENA: status %d' % r.status_code)

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (exc_value))

    if len(title) > 0:
        ret['title'] = title
        ret['url'] = request
    else:
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (root.text))

    return ret


def get_ena_srr_details(srr_id):
    ret = {}

    if len(srr_id) < 5:
        raise ValueError('badly formatted sequence set accession number: %s' % (srr_id))

    try:
        r = requests.get('https://www.ebi.ac.uk/ena/browser/api/xml/%s' % srr_id)
        if r.status_code != 200:
            raise ValueError('Unexpected response from ENA: status %d' % r.status_code)

        root = ET.fromstring(r.content)

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (exc_value))

    titles = root.findall("./EXPERIMENT/TITLE")

    if len(titles) == 0:
        titles = root.findall("./RUN/TITLE")

    if len(titles) > 0:
        ret['title'] = titles[0].text
        ret['url'] = 'https://www.ebi.ac.uk/ena/data/view/' + srr_id
    else:
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (root.text))

    return ret

def get_ena_samn_details(sam_id):
    ret = {}

    if len(sam_id) < 5:
        raise ValueError('badly formatted sample accession number: %s' % (sam_id))

    try:
        r = requests.get('https://www.ebi.ac.uk/ena/browser/api/xml/%s' % sam_id)
        if r.status_code != 200:
            raise ValueError('Unexpected response from ENA: status %d' % r.status_code)

        root = ET.fromstring(r.content)
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (exc_value))

    titles = root.findall("./SAMPLE/TITLE")

    if len(titles) > 0:
        ret['title'] = titles[0].text if len(titles) > 0 else ''
        ret['url'] = 'https://www.ebi.ac.uk/ena/data/view/' + sam_id
    else:
        raise ValueError('Error fetching nucleotide info from ENA: %s' % (root.text))

    return ret

