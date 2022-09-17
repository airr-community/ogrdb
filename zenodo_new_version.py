# Deposit a new version of a file at Zenodo if its contents have changed


import requests
import argparse
import os.path
import json
import hashlib

parser = argparse.ArgumentParser(description='Upload a new version of a file to zenodo if its contents have changed')
parser.add_argument('access_token', help='access token to use')
parser.add_argument('deposit_id', help='deposition id (can be that of any version)')
parser.add_argument('filename', help='new filename to upload')
parser.add_argument('filename_version', help='version of new deposition (0 to increment)')

args = parser.parse_args()

resp = None


# helper function that quits if we get an error
def check_response(r, narrative):
    try:
        resp = r.json()
    except:
        resp = None

    if r.status_code >= 300:
        print(f"Zenodo did not {narrative}. Status: {resp['status']} Reason: {resp['message']}")
        if 'errors' in resp:
            for error in resp['errors']:
                if 'message' in error:
                    print(error['message'])
        breakpoint()
        exit(0)
    return resp


# return the md5 checksum of a file
def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


file_checksum = md5(args.filename)

print('Querying deposition to find latest version')

r = requests.get(f"https://sandbox.zenodo.org/api/deposit/depositions/{args.deposit_id}", params={'access_token': args.access_token})
resp = check_response(r, 'return deposition information')
latest_id = resp['links']['latest'].split('/')[-1]


print('Requesting new deposition')
headers = {"Content-Type": "application/json"}
params = {'access_token': args.access_token}
r = requests.post(f"https://sandbox.zenodo.org/api/deposit/depositions/{latest_id}/actions/newversion", params=params, json={}, headers=headers)
resp = check_response(r, 'return valid deposition metadata')


print('Finding upload link')
deposition_url = resp['links']['latest_draft']
deposition_id = deposition_url.split('/')[-1]
metadata = resp['metadata']

r = requests.get(deposition_url, params={'access_token': args.access_token})
resp = check_response(r, 'return deposition information')


print('Deleting old file from deposition')
name_for_file = os.path.basename(args.filename)
bucket_url = resp['links']['bucket']

for file_desc in resp['files']:
    if file_desc['filename'] == name_for_file:
        if file_desc['checksum'] == file_checksum:
            print('File has not been updated: quitting')
            exit(1)
        r = requests.delete(f"{deposition_url}/files/{file_desc['id']}", params={'access_token': args.access_token})
        resp = check_response(r, 'delete old version of file')


print('Uploading new file')
with open(args.filename, "rb") as fp:
    r = requests.put(f"{bucket_url}/{name_for_file}", data=fp, params=params)
    resp = check_response(r, 'upload new file')


print('Creating deposition data')
if args.filename_version == '0':
    try:
        metadata['version'] = str(int(metadata['version']) + 1)
    except:
        print(f"Current version {metadata['version']} is not a number. Can't increment.")
        exit(0)
else:
    metadata['version'] = args.filename_version

del metadata['doi']
data = {
    'metadata': metadata
}

r = requests.put(deposition_url, params={'access_token': args.access_token}, data=json.dumps(data), headers=headers)
resp = check_response(r, 'update metadata')


print('Publishing')
r = requests.post(f"{deposition_url}/actions/publish", params={'access_token': args.access_token})
resp = check_response(r, 'publish the new deposition')
print(f"Publishing successful")

exit(1)
