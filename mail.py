""" Test module for google's gmail api. """

import os
import argparse
import datetime
from typing import Optional, Union, cast, List, Any, Dict

import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httplib2
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from result import Result, Ok, Err, from_exception

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python.json
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
CLIENT_SECRET_FILE = 'mail_secret.json'
APPLICATION_NAME = 'Weekly Programming Problem'

Message = email.message.Message

def get_credentials(flags: argparse.Namespace) -> Any:
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

def init_service() -> Any:
    """ Builds the gmail service. """
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    credentials = get_credentials(flags)
    http = credentials.authorize(httplib2.Http())
    return discovery.build('gmail', 'v1', http=http)

def get_message(service: Any, user_id: str, msg_id: str) -> Message:
    """ Gets a message using the given client. """
    result = service.users().messages().get(userId=user_id,
                                            id=msg_id,
                                            format="raw").execute()
    msg_str = base64.urlsafe_b64decode(result["raw"].encode("ASCII"))
    return email.message_from_bytes(msg_str)

def send(service: Any,
         user_id: str,
         msg: Union[MIMEText, Message],
         thread_id: Optional[str] = None) -> Dict[str, Any]:
    """ Sends the given message. """
    as_bytes = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode("ASCII")}
    if thread_id is not None:
        as_bytes["threadId"] = thread_id
    # print("Sending {}".format(as_bytes))
    result = service.users().messages().send(userId=user_id,
                                             body=as_bytes).execute() # type: Dict[str, Any]
    # print("Sent message with id: {}".format(result["id"]))
    return result

def trash(service: Any, user_id: str, msg_id: str) -> Any:
    """ Puts the given message in the trash. """
    return service.users().messages().trash(userId=user_id, id=msg_id).execute()

def list_messages(service: Any, user_id: str, labels: str = "INBOX") -> Any:
    """ Gets a messages for the given user.
        By default gets messages in the inbox.
    """
    return service.users().messages().list(userId=user_id, labelIds=labels).execute()


def get_address(msg: Message) -> Result[str, str]:
    """ Extracts the addr-spec part from a mailbox. See RFC-822 for details. """
    address = msg["From"]
    if address is None:
        return Err("Message has no sender")
    if "<" in address:
        return Ok(address[address.find("<")+1:-1])
    else:
        return Ok(address)

def get_text_content(msg: Union[Message, MIMEText]) -> Result[str, str]:
    """ Gets the plain text content of a MIME message if it exists.
        If there is no plain text content then the result is None.
    """
    if msg.get_content_type() == "text/plain":
        payload = cast(bytes, msg.get_payload(decode=True))
        return Ok(payload.decode(msg.get_content_charset()))
    elif msg.get_content_type() == "multipart/alternative":
        for part in cast(List[Message], msg.get_payload()):
            content = get_text_content(part)
            if content.is_ok:
                return content
        return Err("No text/plain alternative found")
    else:
        return Err("Unknown content type: {}".format(msg.get_content_type()))


def make_message(body: str,
                 subject: str,
                 recipient: str,
                 subtype: str = "plain",
                 **other_headers: str) -> MIMEText:
    """ Builds a mime message from the given information. """
    message = MIMEText(body, subtype)
    message["Subject"] = subject
    message["To"] = recipient
    message["From"] = "RoboTobo <tobin.spam@gmail.com>"
    for key, value in other_headers.items():
        message[key] = value
    return message

def clean(html: str) -> str:
    """ Cleans some html text for use in a plain text alternative. """
    # Gmail will do this automatically
    return html

def make_html_message(body: str,
                      subject: str,
                      recipient: str,
                      **other_headers: str) -> MIMEMultipart:
    """ Builds an html mime message from the given information. """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["To"] = recipient
    message["From"] = "RoboTobo <tobin.spam@gmail.com>"
    for key, value in other_headers.items():
        message[key] = value
    message.attach(MIMEText(clean(body), "plain"))
    message.attach(MIMEText(body, "html"))
    return message

def quote(message: Message) -> Result[str, str]:
    """ Quote the text from a message for a reply. """
    if message["Date"] is None:
        return Err("Message has no Date header")

    date_parser = from_exception(datetime.datetime.strptime, ValueError, str)
    date = date_parser(message["Date"], "%a, %d %b %Y %X %z")
    date_str = date.fmap(lambda d: d.strftime("%a, %b %d, %Y at %I:%M %p"))

    content = get_text_content(message)

    def from_content(content_str: str, date_prefix: str) -> str: # pylint: disable=C0111
        quoted = "\r\n".join("> " + line for line in content_str.split("\r\n"))
        return "On {} {} wrote:\r\n\r\n{}\r\n".format(date_prefix, message["From"], quoted)

    return date_str.bind(lambda d: content.fmap(lambda c: from_content(c, d))) # pylint: disable=E0602

def make_reply(message: Message, body: str) -> Result[str, MIMEText]:
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

    quoted = quote(message).extract(lambda _: "", lambda q: q)

    return Ok(make_message(body="{}\r\n\r\n{}".format(body, quoted),
                           subject=subject,
                           recipient=recipient,
                           **{"In-Reply-To": message_id,
                              "References": refs}))
