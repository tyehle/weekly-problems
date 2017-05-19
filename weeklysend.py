""" The script that sends an email out once a week to everybody on the list. """

from typing import Dict, List, Iterable, Any, TypeVar
import datetime
import praw

from result import Result # pylint: disable=W0611
import scraper
import mail
from jsonparse import run_parser_file, dict_parser, list_parser, str_parser

# pylint: disable=C0103

Users = Dict[str, Dict[str, List[str]]]
Post = praw.models.reddit.submission.Submission
A = TypeVar("A")

def empty(xs: Iterable[A]) -> bool:
    """ Tests if an iterable is empty. """
    return not bool(xs)

def send_messages(users: Users, service: Any, levels: Dict[str, Post]) -> None:
    """ Send out messages to all the users. """
    level = scraper.choose_level(users)
    for (address, languages) in users.items():
        lang = None
        if empty(languages[level]):
            lang = "a language of your choice"
        else:
            lang = scraper.choose_language(address, languages[level])
        send_message(address, service, level, lang, levels[level])

def send_message(address: str, service: Any, level: str, language: str, post: Post) -> None:
    """ Sends the user a message containing the problem in the given post. """
    title = post.title.split(']')[-1].strip()
    date = datetime.datetime.now().strftime("%G-W%V")
    subject = "[Weekly Programming Problem] {} in {}".format(title, language)
    repo_url = "https://github.com/tyehle/programming-studio"
    push_instructions = ("To push your code to the <a href={url}>studio repo</a> put "+
                         "it in this week's folder in a folder with your name "+
                         "(ie: {date}/tobin/*.py), or as a single file with "+
                         "your name in it (ie: {date}/tobin_code.py)."
                        ).format(date=date, url=repo_url)
    message = """This week you will be doing the {level}
                 <a href=https://www.reddit.com{link}>{title}</a> problem in
                 {language}!<br><br>

                 {repo}<br><br>

                 {spec}
                 """.format(level=level,
                            title=title,
                            language=language,
                            repo=push_instructions,
                            link=post.permalink,
                            spec=post.selftext_html)
    # print("Sending ({}, {}) to {}".format(level, language, address))
    # if address == "tobinyehle@gmail.com":
    #     print(subject)
    #     without_newlines = message.replace("\n", "")
    #     print(without_newlines)
    mail.send(service, "me", mail.make_html_message(body=message,
                                                    subject=subject,
                                                    recipient=address))

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
            lambda l: send_messages(u, service, l))) # type: Result[str, None] # pylint: disable=E0602

    _ = result.map_err(lambda err: mail_error(service, err)) # type: Result[None, None]
    return result.extract(lambda _: 1, lambda _: 0)

if __name__ == "__main__":
    exit(main())
