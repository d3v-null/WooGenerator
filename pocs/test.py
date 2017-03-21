import httplib2
import os

from apiclient import discovery, errors, http
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://spreadsheets.google.com/feeds https://docs.google.com/feeds'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def download_file(service, drive_file):
    """Download a file's content.

    Args:
      service: Drive API service instance.
      drive_file: Drive File instance.

    Returns:
      File's content if successful, None otherwise.
    """
    download_url = drive_file.get('downloadUrl')
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


def download_file_csv(service, drive_file):
    """Download a file's content.

    Args:
      service: Drive API service instance.
      drive_file: Drive File instance.

    Returns:
      File's content if successful, None otherwise.
    """
    print(type(drive_file))
    print(drive_file)
    download_url = drive_file['exportLinks']['text/csv']
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


def download_media_csv(service, fildId, local_fd):
    request = service.files().get_media(fileId=fildId, acknowledgeAbuse=True)
    print (request), dir(request), dir(request.uri), request.uri
    media_request = http.MediaIoBaseDownload(local_fd, request)
    while True:
        try:
            download_progress, done = media_request.next_chunk()
        except errors.HttpError as error:
            print 'An error occurred: %s' % error
            return
        if download_progress:
            print 'Download Progress: %d%%' % int(download_progress.progress() * 100)
        if done:
            print 'Download Complete'
            return


def main():
    credentials = get_credentials()
    auth_http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=auth_http)

    genFID = "1ps0Z7CYN4D3fQWTPlKJ0cjIkU-ODwlUnZj7ww1gN3xM"

    drive_file = service.files().get(fileId=genFID).execute()
    print drive_file['exportLinks']['text/csv']

    # with open("test.csv") as testFD:
    #     download_media_csv(service, genFID, testFD)

    # genFile = service.files().get_media(fileId=genFID, acknowledgeAbuse=True).execute()

    # csv = download_file_csv(service, genFile)

    # print (csv)

    # results = service.files().list(maxResults=10).execute()
    # items = results.get('items', [])
    # if not items:
    #     print('No files found.')
    # else:
    #     print('Files:')
    #     for item in items:
    #         print('{0} ({1})'.format(item['title'], item['id']))

if __name__ == '__main__':
    main()
