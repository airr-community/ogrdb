# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Functions to manage deposition of germline sets on Zenodo

import zenodo

submission_metadata_template = {
    'access_right': 'open',
    'communities': [{'identifier': 'zenodo'}],
    'creators': [{'affiliation': 'Birkbeck College', 'name': 'Lees, William', 'orcid': '0000-0001-9834-6840'}],
    'description': '<p>IG Germline Reference set published on the Open Germline Receptor Database (OGRDB)</p>',
    'keywords': ['AIRR-seq', 'AIRR Community', 'IG Receptor', 'Antibody', 'T Cell', 'Receptor Repertoire', 'Immunology'],
    'license': 'other-open',
    'publication_date': '2022-09-21',
    'related_identifiers': [{'identifier': 'https://ogrdb.airr-community.org/', 'relation': 'isPublishedIn', 'resource_type': 'dataset', 'scheme': 'url'}],
    'title': 'IG receptor Mouse Germline Set IGKJ (all strains)',
    'upload_type': 'dataset',
    'version': '1'
}

def create_new_series():
    pass

