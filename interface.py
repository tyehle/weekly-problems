""" The interface to the mailer. """

import email
from email.mime.text import MIMEText
from typing import Dict, List, TypeVar, Callable, Any # pylint: disable=unused-import
import json
import re

from result import Result, Err, Ok
import mail
import weeklysend
from jsonparse import run_parser, dict_parser, list_parser, str_parser
from user import User, load_users, save_users

Langs = Dict[str, List[str]] # pylint: disable=invalid-name
Users = Dict[str, User] # pylint: disable=invalid-name
Message = email.message.Message # pylint: disable=invalid-name
Reaction = Callable[[Users, Message], Result[str, MIMEText]] # pylint: disable=invalid-name

A = TypeVar("A")
B = TypeVar("B")

LEVELS = ["Easy", "Intermediate", "Hard"]


def parse_langs(raw: str) -> Result[str, Langs]:
    """ Parse some raw json into the language list. """
    def normalize_keys(langs: Langs) -> Result[str, Langs]: # pylint: disable=missing-docstring
        out = {key.title(): value for key, value in langs.items()}
        for key in out.keys():
            if key not in LEVELS:
                return Err("Not a valid level: {}".format(key))
        return Ok(out)
    parser = dict_parser(list_parser(str_parser))
    return run_parser(raw, parser).bind(normalize_keys)


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
                "remove": modify_user(remove_langs),
                "veto": modify_user(veto),
                "fuck this": modify_user(veto)
               } # type: Dict[str, Reaction]
    return commands.get(subject.lower(), unknown)(users, message)


def modify_user(modify: Callable[[Users, Message, str], Result[str, MIMEText]]) -> Reaction:
    """ Build a function that modifies a user's data. """
    def inner(users: Users, message: Message) -> Result[str, MIMEText]:
        """ Do checks, then run the modify function. """
        def check_and_modify(address: str) -> Result[str, MIMEText]:
            """Check if a user is in the list before proceeding with the modification"""
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
    def with_address(address: str) -> Result[str, MIMEText]: # pylint: disable=missing-docstring
        if address in users:
            return mail.make_reply(message, "{} is already subscribed.".format(address))

        data = mail.get_text_content(message).bind(parse_langs)
        langs = init(data.extract(
            err_func=lambda _: dict(),
            ok_func=lambda l: l
        ))
        user = User(langs, vetoed=False, last_lang=None, last_level=None)
        users[address] = user

        reply = data.extract(
            err_func=("Could not parse json. Failed with {}. " +
                      "You have been subscribed with no languages set.").format,
            ok_func=lambda _: "You have been subscribed with languages set to\r\n{}".format(
                json.dumps(langs, indent=4)
            )
        )

        return mail.make_reply(message, reply)

    return mail.get_address(message).bind(with_address)


def unsub(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """Unsubscribe the sender of the message from the list."""
    users.pop(address)
    return mail.make_reply(message, "{} has been unsubscribed.".format(address))


def get_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Gets the languages listed for the sender. """
    reply = "Languages for {}:\n{}".format(address,
                                           json.dumps(users[address].langs, indent=4))
    return mail.make_reply(message, reply)


def set_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Set the sender's languages to the ones in the message. """
    def set_and_reply(langs: Langs) -> Result[str, MIMEText]:
        """Set the user's languages and build a reply email"""
        users[address].langs = langs
        reply = "Languages for {} have been set to\n{}".format(address, json.dumps(langs, indent=4))
        return mail.make_reply(message, reply)

    parsed_langs = mail.get_text_content(message).bind(parse_langs).fmap(init)
    return parsed_langs.extract(
        err_func=lambda err: mail.make_reply(message, err),
        ok_func=set_and_reply
    )


def add_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Add languages to the sender's list. """
    result = mail.get_text_content(message)\
                 .bind(parse_langs)\
                 .fmap(lambda langs: add(users[address].langs, langs)) # type: Result[str, None]

    good_text = "Language update successful. Languages are now\n{}".format(
        json.dumps(users[address].langs, indent=4))
    reply = result.extract(lambda err: err, lambda _: good_text)

    return mail.make_reply(message, reply)


def remove_langs(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """ Remove languages from the sender's list. """
    result = mail.get_text_content(message)\
                 .bind(parse_langs)\
                 .fmap(lambda langs: remove(users[address].langs, langs)) # type: Result[str, None]

    good_text = "Language update successful. Languages are now\n{}".format(
        json.dumps(users[address].langs, indent=4))
    reply = result.extract(lambda err: err, lambda _: good_text)

    return mail.make_reply(message, reply)


def veto(users: Users, message: Message, address: str) -> Result[str, MIMEText]:
    """Veto this week's problem.

    If half or more of the users veto the problem then send out a new problem to all users.

    Args:
        users: The state of all users
        message: The message from the user
        address: The address of the user

    Returns:
        An error as a string or a reply email
    """
    users[address].vetoed = True
    return mail.make_reply(message, "Your voice has been heard.")


def respond_to_all(service: Any, users: Users) -> None:
    """ Responds to all messages in the inbox. """
    def reply_and_trash(del_id: str, thread_id: str, reply: MIMEText) -> None:
        """ Send a reply, then trash the original message. """
        mail.send(service, "me", reply, thread_id)
        mail.trash(service, "me", del_id)

    # without this definition mypy cannot infer the type of extract
    def fail_mail(err: str) -> None: # pylint: disable=missing-docstring
        notify_failure(service, err)

    for message_data in mail.list_messages(service, "me").get("messages", []):
        msg_id = message_data["id"]
        thread = message_data["threadId"]
        message = mail.get_message(service, "me", msg_id)
        response = react(users, message) # type: Result[str, MIMEText]
        response.extract(
            err_func=fail_mail,
            ok_func=lambda reply: reply_and_trash(msg_id, thread, reply) # pylint: disable=cell-var-from-loop
        )

    vetoes = sum(1 for user in users.values() if user.vetoed)
    if vetoes >= len(users) / 2:
        weeklysend.resend_cause_veto(users, service)


def notify_failure(service: Any, err: str) -> None:
    """ Send an email indicating a failure. """
    message = mail.make_message(body=err,
                                subject="FAILURE",
                                recipient="tobinyehle@gmail.com")
    mail.send(service, "me", message)


def main() -> None:
    """ Function to run if this file is run as a script. """
    service = mail.init_service()

    parsed_users = load_users()

    # without this definition mypy cannot infer the type of extract
    def fail_mail(err: str) -> None: # pylint: disable=missing-docstring
        notify_failure(service, err)

    def respond_and_save(users: Users) -> None:
        """Respond to all messages, then save the user state"""
        respond_to_all(service, users)
        save_users(users)

    parsed_users.extract(err_func=fail_mail, ok_func=respond_and_save)

if __name__ == "__main__":
    main()
