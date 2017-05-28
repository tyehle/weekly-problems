""" The interface to the mailer. """

import email
from email.mime.text import MIMEText
from typing import Dict, List, TypeVar, Callable, Any # pylint: disable=W0611
import json
import re

from result import Result, Err, Ok
import mail
from jsonparse import run_parser, run_parser_file, dict_parser, list_parser, str_parser

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
    def normalize_keys(langs: Langs) -> Result[str, Langs]: # pylint: disable=C0111
        out = {key.title(): value for key, value in langs.items()}
        for key in out.keys():
            if key not in LEVELS:
                return Err("Not a valid level: {}".format(key))
        return Ok(out)
    langs = run_parser(raw, dict_parser(list_parser(str_parser)))
    return langs.bind(normalize_keys)

def add(base: Langs, langs: Langs) -> None:
    """ Adds the languages to the given dictionary. """
    for level in LEVELS:
        for lang in langs.get(level, []):
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
                "?": help_msg,
                "subscribe": sub,
                "unsubscribe": modify_user(unsub),
                "get": modify_user(get_langs),
                "set": modify_user(set_langs),
                "add": modify_user(add_langs),
                "remove": modify_user(remove_langs)
               } # type: Dict[str, Reaction]
    return commands.get(subject.lower(), unknown)(users, message)

def modify_user(modify: Callable[[Users, Message, str], Result[str, MIMEText]]) -> Reaction:
    """ Build a function that modifies a user's data. """
    def inner(users: Users, message: Message) -> Result[str, MIMEText]:
        """ Do checks, then run the modify function. """
        def check_and_modify(address: str) -> Result[str, MIMEText]: # pylint: disable=C0111
            if address not in users:
                return mail.make_reply(message, "{} is not subscribed.".format(address))
            else:
                return modify(users, message, address)

        return mail.get_address(message).bind(check_and_modify)
    return inner

def help_msg(_: Users, message: Message) -> Result[str, MIMEText]:
    """ Builds an email containing the help information. """
    info = """Available commands are subscribe, unsubscribe, get, set, add, remove, and help."""
    return mail.make_reply(message, info)

def unknown(users: Users, message: Message) -> Result[str, MIMEText]:
    """ Handle a message with an unknown command. """
    subject = message["subject"]
    if subject is not None and re.match("fu+c?k yo*u+", subject.lower()):
        return mail.make_reply(message, "Fuck you too bitch, call the cops!")
    else:
        return help_msg(users, message)

def sub(users: Users, message: Message) -> Result[str, MIMEText]:
    """ Subscribes the sender to the list with the contents.
        If the contents fail to parse, the new user gets an empty dict,
        an error message, and the help reply.
    """
    def with_address(address: str) -> Result[str, MIMEText]: # pylint: disable=C0111
        if address in users:
            return mail.make_reply(message, "{} is already subscribed.".format(address))

        data = mail.get_text_content(message).bind(parse_langs)
        langs = init(data.extract(lambda _: dict(), lambda l: l))
        users[address] = langs

        reply = data.extract(("Could not parse json. Failed with {}. You have " +
                              "been subscribed with no languages set.").format,
                             lambda _: "You have been subscribed with languages " +
                             "set to\r\n{}".format(json.dumps(langs, indent=4)))

        return mail.make_reply(message, reply)

    return mail.get_address(message).bind(with_address)

def unsub(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Unsubscribe the sender of the message from the list. """
    users.pop(address)
    return mail.make_reply(message, "{} has been unsubscribed.".format(address))

def get_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Gets the languages listed for the sender. """
    reply = "Langues for {}:\n{}".format(address,
                                         json.dumps(users[address], indent=4))
    return mail.make_reply(message, reply)

def set_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Set the sender's languages to the ones in the message. """
    langs = mail.get_text_content(message).bind(parse_langs).fmap(init)

    def set_and_reply(ls: Langs) -> Result[str, MIMEText]: # pylint: disable=C0111
        users[address] = ls
        reply = "Languages for {} have been set to\n{}".format(address, json.dumps(ls, indent=4))
        return mail.make_reply(message, reply)

    return langs.extract(lambda err: mail.make_reply(message, err), set_and_reply)

def add_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Add languages to the sender's list. """
    result = mail.get_text_content(message)\
                 .bind(parse_langs)\
                 .fmap(lambda langs: add(users[address], langs)) # type: Result[str, None]

    good_text = "Language update successful. Languages are now\n{}".format(
        json.dumps(users[address], indent=4))
    reply = result.extract(lambda err: err, lambda _: good_text)

    return mail.make_reply(message, reply)

def remove_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Remove languages from the sender's list. """
    result = mail.get_text_content(message)\
                 .bind(parse_langs)\
                 .fmap(lambda langs: remove(users[address], langs)) # type: Result[str, None]

    good_text = "Language update successful. Languages are now\n{}".format(
        json.dumps(users[address], indent=4))
    reply = result.extract(lambda err: err, lambda _: good_text)

    return mail.make_reply(message, reply)

def respond_to_all(service: Any, users: Users) -> None:
    """ Responds to all messages in the inbox. """
    def reply_and_trash(message_data: Dict[str, str], reply: MIMEText) -> None:
        """ Send a reply, then trash the original message. """
        mail.send(service, "me", reply, message_data["threadId"])
        mail.trash(service, "me", message_data["id"])

    # without this definition mypy cannot infer the type of extract
    def fail_mail(err: str) -> None: # pylint: disable=C0111
        notify_failure(service, err)

    for message_data in mail.list_messages(service, "me").get("messages", []):
        message = mail.get_message(service, "me", message_data["id"])
        response = react(users, message) # type: Result[str, MIMEText]
        response.extract(fail_mail,
                         lambda reply: reply_and_trash(message_data, reply))

    json.dump(users, open("users.json", 'w'), indent=4)

def notify_failure(service: Any, err: str) -> None:
    """ Send an email indicating a failure. """
    message = mail.make_message(body=err,
                                subject="FAILURE",
                                recipient="tobinyehle@gmail.com")
    mail.send(service, "me", message)

def main() -> None:
    """ Function to run if this file is run as a script. """
    service = mail.init_service()

    user_parser = dict_parser(dict_parser(list_parser(str_parser)))
    users = run_parser_file("users.json", user_parser) # type: Result[str, Users]

    # without this definition mypy cannot infer the type of extract
    def fail_mail(err: str) -> None: # pylint: disable=C0111
        notify_failure(service, err)

    users.extract(fail_mail, lambda u: respond_to_all(service, u))

if __name__ == "__main__":
    main()
