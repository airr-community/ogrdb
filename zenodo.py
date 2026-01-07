# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#
# Deposit a new version of a file at Zenodo if its contents have changed


import requests
import argparse
import os.path
import json
import hashlib
import logging
import importlib


# helper function that throws if we get an error
class ZenodoException(Exception):
    pass

def check_response(r, narrative):

    try:
        if r.status_code < 300 and r.reason == 'NO CONTENT':
            return {}

        resp = r.json()
    except Exception as e:
        raise ZenodoException(e)

    if r.status_code >= 300:
        error_message = f"Zenodo did not {narrative}. Status: {resp['status']} Reason: {resp['message']}"
        if 'errors' in resp:
            for error in resp['errors']:
                if 'message' in error:
                    error_message += '\n' + error['message']

        raise ZenodoException(error_message)

    return resp


# return the md5 checksum of a file
def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def read_zenodo_creds(filename):
    secrets = {}

    with open(filename, 'r') as fi:
        for line in fi:
            if 'ZENODO' in line and '=' in line:
                k, v = line.split('=')
                k = k.replace(' ', '')
                v = v.replace("'", "")
                v = v.replace(' ', '')
                v = v.replace('\n', '')
                secrets[k] = v

    return secrets


# Check for a deposition in Zenodo that matches our title
# this is used as a check to avoid double depositions
def zenodo_check_for_title(zenodo_url, access_token, title):
    r = requests.get(f"{zenodo_url}/api/records",
                            params={'q': f'"{title}"',
                                    'status': 'published',
                                    'access_token': access_token})

    resp = check_response(r, 'return deposition information')
    return len(resp['hits']['hits']) > 0



# Create a new upload
# This is only used when we want to create a new *series* of depositions
# Use zenodo_new_version to update files in a series
def zenodo_new_deposition(zenodo_url, access_token, metadata):
    try:
        logging.warning('Checking for existing title')
        if zenodo_check_for_title(zenodo_url, access_token, metadata['title']):
            raise ZenodoException('A published deposition with that title already exists.')

        logging.warning('Creating deposition')
        r = requests.post(f"{zenodo_url}/api/deposit/depositions",
                          params={'access_token': access_token},
                          json={'metadata': metadata},
                          headers={"Content-Type": "application/json"})

        resp = check_response(r, 'return deposition information')
        deposition_id = resp['id']

    except ZenodoException as e:
        logging.error(str(e))
        return False, str(e)

    return True, deposition_id


# Create a new deposition in a series. Delete any previous files and add new ones specified in the arguments
# Files can either be specified as pathnames, or as filename/file description pairs
def zenodo_new_version(zenodo_url, access_token, deposit_id, filenames, file_string_pairs, new_version):
    try:
        logging.warning('Querying deposition to find latest version')

        params = {'access_token': access_token}
        headers = {"Content-Type": "application/json"}

        # fetch the record to find the latest version

        r = requests.get(f"{zenodo_url}/api/deposit/depositions/{deposit_id}", params=params)
        resp = check_response(r, 'return records')

        latest_id = resp['links']['latest_draft'].split('/')[-1]

        r = requests.get(f"{zenodo_url}/api/records/{latest_id}", params=params)

        # if this is the very first deposition, we'll get this error when querying for the latest version
        # ... but in that case we know we already have it
        if not (r.status_code == 404 and 'identifier is not registered' in r.text):
            resp = check_response(r, 'return records')

        if 'latest_draft' not in resp['links']:
            logging.warning('Requesting new draft deposition')
            r = requests.post(f"{zenodo_url}/api/deposit/depositions/{latest_id}/actions/newversion", params=params, json={}, headers=headers)
            resp = check_response(r, 'return valid deposition metadata')
            # a failure here probably means that the draft was created before but isn't showing
            # only way to fix seems to be to create a draft in the UI, then discard it

        logging.warning('Finding upload link')
        deposition_url = resp['links']['latest_draft']
        metadata = resp['metadata']

        r = requests.get(deposition_url, params=params)
        resp = check_response(r, 'return deposition information')

        logging.warning('Deleting old files from deposition')
        bucket_url = resp['links']['bucket']

        for file_desc in resp['files']:
            r = requests.delete(f"{deposition_url}/files/{file_desc['id']}", params=params)
            resp = check_response(r, 'delete old version of file')

        logging.warning('Uploading new files')
        for filename in filenames:
            with open(filename, "rb") as fp:
                r = requests.put(f"{bucket_url}/{os.path.basename(filename)}", data=fp, params=params)
                resp = check_response(r, 'upload new file')

        for fp, filename in file_string_pairs:
            r = requests.put(f"{bucket_url}/{os.path.basename(filename)}", data=fp, params=params)
            resp = check_response(r, 'upload new file')

        logging.warning('Creating deposition data')
        if new_version == '0':
            try:
                if 'version' in metadata:
                    metadata['version'] = str(int(metadata['version']) + 1)
                else:
                    metadata['version'] = '1'
            except:
                error_message = f"Current version {metadata['version']} is not a number. Can't increment."
                logging.error(error_message)
                return False,
        else:
            metadata['version'] = new_version

        if 'doi' in metadata:
            del metadata['doi']
            
        data = {
            'metadata': metadata
        }

        r = requests.put(deposition_url, params=params, data=json.dumps(data), headers=headers)
        resp = check_response(r, 'update metadata')

        logging.warning('Publishing')
        r = requests.post(f"{deposition_url}/actions/publish", params=params)
        resp = check_response(r, 'publish the new deposition')

        logging.warning(f"Publishing successful")
        return True, resp

    except ZenodoException as e:
        logging.error(str(e))
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='Upload a new version of a file to zenodo')
    parser.add_argument('deposit_id', help='deposition id (can be that of any version)')
    parser.add_argument('filenames', help='filenames to upload (separated by ,)')
    parser.add_argument('filename_version', help='version of new deposition (0 to increment)')
    args = parser.parse_args()

    if not os.path.isfile('secret.cfg'):
        logging.error('secret.cfg must be in the current directory')
        exit(1)

    secrets = read_zenodo_creds('secret.cfg')

    ret = zenodo_new_version(secrets['ZENODO_URL'], secrets['ZENODO_ACCESS_TOKEN'], args.deposit_id, args.filenames.split(','), [], args.filename_version)
    exit(ret)

if __name__ == "__main__":
    main()
