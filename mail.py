""" Test module for google's gmail api. """

import os
import json
import argparse
import datetime
from typing import Optional, Union, cast, List

import base64
import email
from email.mime.text import MIMEText
import httplib2
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from result import Result, Ok, Err

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python.json
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
CLIENT_SECRET_FILE = 'mail_secret.json'
APPLICATION_NAME = 'Weekly Programming Problem'


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
                                   'gmail-python.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

def init_service():
    """ Builds the gmail service. """
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    credentials = get_credentials(flags)
    http = credentials.authorize(httplib2.Http())
    return discovery.build('gmail', 'v1', http=http)

def get_message(service, user_id, msg_id):
    """ Gets a message using the given client. """
    result = service.users().messages().get(userId=user_id,
                                            id=msg_id,
                                            format="raw").execute()
    msg_str = base64.urlsafe_b64decode(result["raw"].encode("ASCII"))
    return email.message_from_bytes(msg_str)

def get_text_content(msg: Union[email.message.Message, MIMEText]) -> Result[str, str]:
    """ Gets the plain text content of a MIME message if it exists.
        If there is no plain text content then the result is None.
    """
    if msg.get_content_type() == "text/plain":
        payload = cast(bytes, msg.get_payload(decode=True))
        return Ok(payload.decode(msg.get_content_charset()))
    elif msg.get_content_type() == "multipart/alternative":
        for part in cast(List[email.message.Message], msg.get_payload()):
            content = get_text_content(part)
            if content.is_ok:
                return content
        return Err("No text/plain alternative found")
    else:
        return Err("Unknown content type: {}".format(msg.get_content_type()))

def make_message(body: str,
                 subject: str,
                 recipient: str,
                 sender: str,
                 alias: Optional[str]=None,
                 **other_headers: str) -> MIMEText:
    """ Builds a raw mime message from the given information. """
    message = MIMEText(body)
    message["Subject"] = subject
    message["To"] = recipient
    if alias is not None:
        message["From"] = "{} <{}>".format(alias, sender)
    else:
        message["From"] = sender
    for key, value in other_headers.items():
        message[key] = value
    return message

def send(service, user_id, msg, thread_id=None):
    """ Sends the given message. """
    as_bytes = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode("ASCII")}
    if thread_id is not None:
        as_bytes["threadId"] = thread_id
    print("Sending {}".format(as_bytes))
    result = service.users().messages().send(userId=user_id, body=as_bytes).execute()
    print("Sent message with id: {}".format(result["id"]))
    return result

def trash(service, user_id, msg_id):
    """ Puts the given message in the trash. """
    return service.users().messages().trash(userId=user_id, id=msg_id).execute()

def list_messages(service, user_id, labels="INBOX"):
    """ Gets a messages for the given user.
        By default gets messages in the inbox.
    """
    return service.users().messages().list(userId=user_id, labelIds=labels).execute()

def quote(message: MIMEText) -> Result[str, str]:
    """ Quote the text from a message for a reply. """
    if message["Date"] is None:
        return Err("Message has no Date header")

    date = datetime.datetime.strptime(message["Date"], "%a, %d %b %Y %X %z")
    date_prefix = date.strftime("%a, %b %d, %Y at %I:%M %p")

    content = get_text_content(message)

    def from_content(content_str: str) -> str: # pylint: disable=C0111
        quoted = "\r\n".join("> " + line for line in content_str.split("\r\n"))
        return "On {} {} wrote:\r\n\r\n{}\r\n".format(date_prefix, message["From"], quoted)

    return content.mapOk(from_content)

def make_reply(message: MIMEText, body: str, alias: Optional[str]=None) -> Result[str, MIMEText]:
    """ Create a message in reply to another message. """
    recipient = message.get("Reply-To", failobj=message["From"])
    message_id = message["Message-ID"]
    orig_subject = message["Subject"]

    # make sure we have the required fields
    if recipient is None:
        return Err("Message has no From or Reply-To header")
    if message_id is None:
        return Err("Message has no Message-ID header")
    if orig_subject is None:
        return Err("Message has no Subject header")

    subject = orig_subject if "Re: " in orig_subject else "Re: " + orig_subject

    refs = message.get("References", failobj="") + " " + message_id
    refs = refs.strip() # remove the leading space if the get failed

    return Ok(make_message(body="{}\r\n\r\n{}".format(body, quote(message)),
                           subject=subject,
                           recipient=recipient,
                           sender="tobin.spam@gmail.com",
                           alias=alias,
                           **{"In-Reply-To": message_id,
                              "References": refs}))

def main() -> None:
    """ Creates a Gmail API service object and outputs a list of label names
        of the user's Gmail account.
    """
    service = init_service()

    out = make_message(body="Hey look I changed my picture!",
                       subject="Test Message",
                       recipient="tobinyehle@gmail.com",
                       sender="tobin.spam@gmail.com",
                       alias="RoboTobo")
    # send(service, "me", out)

    messages = list_messages(service, user_id='me')
    for msg in messages.get("messages", []):
        message = get_message(service, "me", msg["id"])
        content = get_text_content(message)

        if "Delete" in message["subject"]:
            print("Found a message to delete!")
            print(message["subject"])
            print("deleting message with id: " + msg["id"])
            # deleted = trash(service, "me", msg["id"])
            # print(deleted)

        if "Modify" in message["subject"]:
            print("found a modify message!")
            reply = make_reply(message, "This service is not yet implemented", alias="RoboTobo")
            print(reply)
            # send(service, "me", reply, msg["threadId"])

        print(content)
        print(msg)
        headers = {k: message[k] for k in message.keys()}
        print("Message details:\n{}".format(json.dumps(headers, indent=2)))


if __name__ == '__main__':
    main()
