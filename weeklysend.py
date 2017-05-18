""" The script that sends an email out once a week to everybody on the list. """

from typing import Any

from result import Result # pylint: disable=W0611
import scraper
import mail
from jsonparse import run_parser_file, dict_parser, list_parser, str_parser

def mail_error(service: Any, message: str) -> None:
    """ Mail an error message. """
    email = mail.make_message(body=message,
                              subject="FAILURE",
                              recipient="tobinyehle@gmail.com")
    mail.send(service, "me", email)

def main() -> int:
    """ The main function to run when this file is called as a script. """
    service = mail.init_service()

    user_parser = dict_parser(dict_parser(list_parser(str_parser)))
    users = run_parser_file("users.json", user_parser)

    levels = scraper.init_reddit().bind(scraper.latest)

    result = users.bind(
        lambda u: levels.fmap(
            lambda l: scraper.send_messages(u, service, l))) # type: Result[str, None]

    _ = result.map_err(lambda err: mail_error(service, err)) # type: Result[None, None]
    return result.extract(lambda _: 1, lambda _: 0)

if __name__ == "__main__":
    exit(main())
