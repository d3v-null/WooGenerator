# pip install google-api-python-client
import httplib2
import os

from googleapiclient import discovery
import oauth2client
from oauth2client import client, tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://spreadsheets.google.com/feeds https://docs.google.com/feeds'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Laserphile WooGenerator Drive API'

genFID = "1ps0Z7CYN4D3fQWTPlKJ0cjIkU-ODwlUnZj7ww1gN3xM"
genGID = "784188347"


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'drive-woogenerator.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def download_file_gid_csv(service, drive_file, gid):
    """Download a file's content.

    Args:
      service: Drive API service instance.
      drive_file: Drive File instance.

    Returns:
      File's content if successful, None otherwise.
    """
    print( type(drive_file) )
    print( drive_file)
    download_url = drive_file['exportLinks']['text/csv']
    if gid:
        download_url += "?gid=" + gid 
    print download_url
    if download_url:
      resp, content = service._http.request(download_url)
      if resp.status == 200:
        print ('Status: %s' % resp)
        return content
      else:
        print ('An error occurred: %s' % resp)
        return None
    else:
      # The file doesn't have any content stored on Drive.
      return None  

def main():
    credentials = get_credentials()
    auth_http = credentials.authorize(httplib2.Http())
    print repr(auth_http)
    service = discovery.build('drive', 'v2', http=auth_http)
    print repr(service)
    drive_file = service.files().get(fileId=genFID).execute()
    content = download_file_gid_csv(service, drive_file, )
    print content


if __name__ == '__main__':
    main()