""" Test module for google's gmail api. """

import os
import json
import argparse
import base64

import httplib2
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CLIENT_SECRET_FILE = 'mail_secret.json'
APPLICATION_NAME = 'Gmail API Python Quickstart'


def get_credentials(flags):
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
                                   'gmail-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_contents(msg):
    """ Gets the contents of a message. """
    payload = msg["payload"]

    if payload["mimeType"] == "multipart/alternative":
        parts = payload["parts"]
        by_type = {part["mimeType"]: part for part in parts}
        if "text/plain" in by_type:
            contents = base64.urlsafe_b64decode(by_type["text/plain"]["body"]["data"]).decode()
            return contents
        else:
            print("No plain text type found!")
            return None
    else:
        print("Unknown message type: {}".format(payload["mimeType"]))
        return None

def lookup(name, store, default=None):
    """ Looks up the name in the given store.
        If the name is not found then the default value is returned.
        If the no default is given then None is returned.
    """
    return next((x["value"] for x in store if x["name"] == name), default)

def main():
    """Shows basic usage of the Gmail API.

    Creates a Gmail API service object and outputs a list of label names
    of the user's Gmail account.
    """
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    credentials = get_credentials(flags)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    messages = service.users().messages().list(userId='me', labelIds="INBOX").execute()
    for msg in messages.get("messages", []):
        results = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = results["payload"]["headers"]
        subject = lookup("Subject", headers)
        recipient = lookup("To", headers)
        sender = lookup("From", headers)
        print("\n\n---------- MESSAGE ----------\nid: {}\nsubject: {}\nto: {}\nfrom: {}\n".format(message_id, subject, recipient, sender))
        print(get_contents(results))
        # print(json.dumps(results, indent=2))

    # to_send = {}
    # service.users().


if __name__ == '__main__':
    main()
