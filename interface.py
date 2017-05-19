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
Reaction = Callable[[Users, Message], Result[str, MIMEText]]

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

def add(base: Langs, langs: Langs) -> None:
    """ Adds the languages to the given dictionary. """
    for level in LEVELS:
        for lang in langs[level]:
            if lang not in base[level]:
                base[level].append(lang)

def remove(base: Langs, to_remove: Langs) -> None:
    """ Removes the languages from the given dictionary. """
    for level in LEVELS:
        if level in to_remove:
            base[level] = [lang for lang in base[level] if lang not in to_remove[level]]

def init(langs: Langs) -> Langs:
    """ Initializes a new languages dict from a given set of languages. """
    new_langs = {level: [] for level in LEVELS} # type: Dict[str, List[str]]
    add(new_langs, langs)
    return new_langs

def react(users: Users, message: Message) -> Result[str, MIMEText]:
    """ Uses the subject line of the given message to update the user list and
        build a response.
    """
    subject = message["Subject"]
    if subject is None:
        return Err("Message has no subject")

    commands = {"help": help_msg,
                "subscribe": sub,
                "unsubscribe": modify_user(unsub),
                "get": modify_user(get_langs),
                "set": modify_user(set_langs),
                "add": modify_user(add_langs),
                "remove": modify_user(remove_langs)
               } # type: Dict[str, Reaction]
    return commands.get(subject.lower(), help_msg)(users, message)

def modify_user(modify: Callable[[Users, Message, str], Result[str, MIMEText]]) -> Reaction:
    """ Build a function that modifies a user's data. """
    def inner(users: Users, message: Message) -> Result[str, MIMEText]:
        """ Do checks, then run the modify function. """
        address = message["From"]
        if address is None:
            return Err("Message has no sender")
        if address not in users:
            return mail.make_reply(message, "{} is not subscribed.".format(address))
        return modify(users, message, address)
    return inner

def help_msg(_: Users, message: Message) -> Result[str, MIMEText]:
    """ Builds an email containing the help information. """
    info = """This is the help message."""
    return mail.make_reply(message, info)

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
    langs = init(data.extract(lambda _: dict(), lambda l: l))
    users[address] = langs

    reply = data.extract(("Could not parse json. Failed with {}. You have " +
                          "been subscribed with no languages set.").format,
                         lambda _: "Languages have been set to\r\n{}".format(
                             json.dumps(langs, indent=2)))

    return mail.make_reply(message, reply)

def unsub(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Unsubscribe the sender of the message from the list. """
    users.pop(address)
    return mail.make_reply(message, "{} has been unsubscribed.".format(address))

def get_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Gets the languages listed for the sender. """
    reply = "Langues for {}:\n{}".format(address,
                                         json.dumps(users[address], indent=2))
    return mail.make_reply(message, reply)

def set_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Set the sender's languages to the ones in the message. """
    langs = mail.get_text_content(message).bind(parse_langs).fmap(init)

    def set_and_reply(ls: Langs) -> Result[str, MIMEText]: # pylint: disable=C0111
        users[address] = ls
        reply = "Languages for {} have been set to\n{}".format(address, ls)
        return mail.make_reply(message, reply)

    return langs.extract(lambda err: mail.make_reply(message, err), set_and_reply)

def add_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Add languages to the sender's list. """
    result = mail.get_text_content(message)\
                 .bind(parse_langs)\
                 .fmap(lambda langs: add(users[address], langs)) # type: Result[str, None]

    good_text = "Language update successful. Languages are now\n{}".format(
        json.dumps(users[address], indent=2))
    reply = result.extract(lambda err: err, lambda _: good_text)

    return mail.make_reply(message, reply)

def remove_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Remove languages from the sender's list. """
    result = mail.get_text_content(message)\
                 .bind(parse_langs)\
                 .fmap(lambda langs: remove(users[address], langs)) # type: Result[str, None]

    good_text = "Language update successful. Languages are now\n{}".format(
        json.dumps(users[address], indent=2))
    reply = result.extract(lambda err: err, lambda _: good_text)

    return mail.make_reply(message, reply)
