""" The script that sends an email out once a week to everybody on the list. """

from typing import Dict, Iterable, Any, TypeVar, Callable, Optional
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


def different_lang(user: User, level: str) -> Optional[str]:
    """Tries to choose a language different than what the user had the previous week.

    Args:
        user: The user to choose the language for
        level: The level of challenge to choose a language for

    Returns:
        The language, or None if the user has no languages for the given level
    """
    if empty(user.langs[level]):
        return None
    else:
        for _ in range(1000):
            lang = scraper.choose(user.langs[level])
            if lang != user.last_lang:
                return lang
        return scraper.choose(user.langs[level])


def same_lang(user: User, level: str) -> Optional[str]:
    """Chooses the same language as the user had the previous week if possible.

    Args:
        user: The user to choose the language for
        level: The level of challenge to choose a language for

    Returns:
        The language, or None if the user has no languages for the given level
    """
    # make sure the user has not changed the language list
    langs = user.langs[level]
    if (user.last_lang is None and empty(langs)
            or user.last_lang in langs):
        return user.last_lang
    else:
        return scraper.choose(langs)


def send_messages(users: Users,
                  service: Any,
                  level: str,
                  post: Post,
                  choose_lang: Callable[[User, str], Optional[str]]
                 ) -> None:
    """ Send out messages to all the users. """
    for (address, user) in users.items():
        lang = choose_lang(user, level)
        lang_str = "a language of your choice" if lang is None else lang
        user.last_lang = lang
        user.vetoed = False
        send_message(address, service, level, lang_str, post)


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


def mail_error(service: Any) -> Callable[[str], None]:
    """Build a function that takes a string and mails a failure message.

    Args:
        service: The service to use to send the message

    Returns:
        The function that mails the error.
    """
    def send_mail(message: str) -> None:
        """ Mail an error message. """
        email = mail.make_message(body=message,
                                  subject="FAILURE",
                                  recipient="tobinyehle@gmail.com")
        mail.send(service, "me", email)

    return send_mail


def resend_cause_veto(users: Users, service: Any) -> None:
    """Send out a new challenge because the last one was vetoed.

    Args:
        users: The user list
        service: The mail service to use
    """
    level = scraper.choose_level(users) # TODO: Don't send the same challenge
    result = scraper.init_reddit().bind(scraper.latest).fmap(
        lambda posts: send_messages(users,
                                    service,
                                    level,
                                    posts[level],
                                    same_lang)) # type: Result[str, None]
    result.extract(
        err_func=mail_error(service),
        ok_func=lambda _: None
    )


def main() -> int:
    """ The main function to run when this file is called as a script. """
    def with_users_posts(users: Users, posts: Dict[str, Post]) -> None:
        """Does all the things that need the user list"""
        level = scraper.choose_level(users)
        send_messages(users, service, level, posts[level], different_lang)
        save_state(users)

    service = mail.init_service()
    result = load_state().bind(
        lambda u: scraper.init_reddit().bind(scraper.latest).fmap(
            lambda ps: with_users_posts(u, ps))) # type: Result[str, None] # pylint: disable=undefined-variable

    return result.map_err(mail_error(service)).extract(
        err_func=lambda _: 1,
        ok_func=lambda _: 0
    )

if __name__ == "__main__":
    exit(main())
