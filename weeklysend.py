""" The script that sends an email out once a week to everybody on the list. """

from typing import Dict, Iterable, Any, TypeVar
import datetime
import praw

from result import Result # pylint: disable=W0611
import scraper
import mail
from state import User, load_state, save_state

# pylint: disable=C0103

Users = Dict[str, User]
Post = praw.models.reddit.submission.Submission
A = TypeVar("A")


def empty(xs: Iterable[A]) -> bool:
    """ Tests if an iterable is empty. """
    return not bool(xs)


def send_messages(users: Users, service: Any, levels: Dict[str, Post]) -> None:
    """ Send out messages to all the users. """
    level = scraper.choose_level(users)
    for (address, user) in users.items():
        if empty(user.langs[level]):
            lang = "a language of your choice"
            user.last_lang = None
        else:
            lang = scraper.choose_language(address, user.langs[level])
            user.last_lang = lang
        user.vetoed = False
        send_message(address, service, level, lang, levels[level])


def send_message(address: str, service: Any, level: str, language: str, post: Post) -> None:
    """ Sends the user a message containing the problem in the given post. """
    title = post.title.split(']')[-1].strip()
    date = datetime.datetime.now().strftime("%G-W%V")
    subject = "[Weekly Programming Problem] {} in {}".format(title, language)
    repo_url = "https://github.com/tyehle/programming-studio"
    push_instructions = ("To push your code to the <a href={url}>studio repo</a> put " +
                         "it in this week's folder in a folder with your name " +
                         "(ie: {date}/tobin/*.py), or as a single file with " +
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


def choose_and_send(users: Users, service: Any) -> Result[str, None]:
    """Choose a level and send messages to all users

    Args:
        users: The users to send to
        service: The email service to use

    Returns:
        None on success or a string with an error message on failure
    """
    levels = scraper.init_reddit().bind(scraper.latest)
    return levels.fmap(lambda l: send_messages(users, service, l))


def main() -> int:
    """ The main function to run when this file is called as a script. """
    def send_and_save(u: Users) -> Result[str, None]:
        """Sends messages then saves the user state"""
        return choose_and_send(u, service).fmap(lambda _: save_state(u))

    def mail_error(message: str) -> None:
        """ Mail an error message. """
        email = mail.make_message(body=message,
                                  subject="FAILURE",
                                  recipient="tobinyehle@gmail.com")
        mail.send(service, "me", email)

    service = mail.init_service()
    users = load_state()
    result = users.bind(send_and_save).map_err(mail_error) # type: Result[None, None]
    return result.extract(
        err_func=lambda _: 1,
        ok_func=lambda _: 0
    )

if __name__ == "__main__":
    exit(main())
