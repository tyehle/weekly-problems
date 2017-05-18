""" The interface to the mailer. """

import email
from email.mime.text import MIMEText
from typing import Dict, List, TypeVar, Callable, Any # pylint: disable=W0611
import json

from result import Result, Err, Ok
import mail
from jsonparse import run_parser, dict_parser, list_parser, str_parser

# pylint: disable=C0103

Langs = Dict[str, List[str]]
Users = Dict[str, Langs]
Message = email.message.Message

A = TypeVar("A")
B = TypeVar("B")

LEVELS = ["Easy", "Intermediate", "Hard"]

def parse_langs(raw: str) -> Result[str, Langs]:
    """ Parse some raw json into the language list. """
    def check_keys(langs: Langs) -> Result[str, Langs]: # pylint: disable=C0111
        for key in langs.keys():
            if key not in LEVELS:
                return Err("Not a valid level: {}".format(key))
        return Ok(langs)
    langs = run_parser(raw, dict_parser(list_parser(str_parser)))
    return langs.bind(check_keys)

def add_languages(base: Langs, langs: Langs) -> None:
    """ Adds the languages to the given dictionary. """
    for level in LEVELS:
        for lang in langs[level]:
            if lang not in base[level]:
                base[level].append(lang)

def remove_languages(base: Langs, to_remove: Langs) -> None:
    """ Removes the languages from the given dictionary. """
    for level in LEVELS:
        if level in to_remove:
            base[level] = [lang for lang in base[level] if lang not in to_remove[level]]

def react(users: Users, message: Message) -> Result[str, MIMEText]:
    """ Uses the subject line of the given message to update the user list and
        build a response.
    """
    subject = message["Subject"]
    if subject is None:
        return Err("Message has no subject")

    commands = {"help": help_msg,
                "subscribe": sub,
                "unsubscribe": unsub
               } # type: Dict[str, Callable[[Users, Message], Result[str, MIMEText]]]
    return commands.get(subject.lower(), help_msg)(users, message)

def help_msg(_: Users, message: Message) -> Result[str, MIMEText]:
    """ Builds an email containing the help information. """
    info = """This is the help message."""
    return mail.make_reply(message, info)

def unsub(users: Users, message: Message) -> Result[str, MIMEText]:
    """ Unsubscribe the sender of the message from the list. """
    address = message["To"]
    if address is None:
        return Err("Message has no sender")

    if address not in users:
        return mail.make_reply(message, "{} is not subscribed.".format(address))

    users.pop(address)
    return mail.make_reply(message, "{} has been unsubscribed.".format(address))

def sub(users: Users, message: Message) -> Result[str, MIMEText]:
    """ Subscribes the sender to the list with the contents.
        If the contents fail to parse, the new user gets an empty dict,
        an error message, and the help reply.
    """
    address = message["From"]
    if address is None:
        return Err("Message has no sender")

    if address in users:
        return mail.make_reply(message, "{} is already subscribed.".format(address))

    data = mail.get_text_content(message).bind(parse_langs)

    new_langs = {level: [] for level in LEVELS} # type: Dict[str, List[str]]
    _ = data.map_ok(lambda langs: add_languages(new_langs, langs)) # type: Result[str, None]
    users[address] = new_langs

    reply = data.extract(("Could not parse json. Failed with {}. You have " +
                          "been subscribed with no languages set.").format,
                         lambda _: "Languages have been set to\r\n{}".format(
                             json.dumps(new_langs, indent=2)))

    return mail.make_reply(message, reply)
