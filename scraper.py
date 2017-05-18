""" Gets the weekly challenge from reddit.com/r/dailyprogrammer """

import sys
import json
import random
import time
from typing import List, Dict, Optional, Callable, Iterable, Any, TypeVar

import praw

from mail import send, make_html_message
from result import Result, Err, Ok
from jsonparse import run_parser_file, dict_parser, list_parser, str_parser

VERSION = "v0.1"
ID = "dailyprogrammer-scraper"
AUTHOR = "/u/ToboRoboLoco"

# pylint: disable=C0103

# Yag = yagmail.SMTP
Reddit = praw.Reddit
Post = praw.models.reddit.submission.Submission
Users = Dict[str, Dict[str, List[str]]]
A = TypeVar("A")
B = TypeVar("B")

def user_agent() -> str:
    """ Build the user agent string """
    return "{}:{}:{} by {}".format(sys.platform, ID, VERSION, AUTHOR)

def init_reddit() -> Result[str, Reddit]:
    """ Gets a praw reddit instance """
    client = run_parser_file("client-info.json", dict_parser(str_parser))
    return client.fmap(lambda c: praw.Reddit(user_agent=user_agent(), **c))

def get_date() -> str:
    """ Gets the current date in the ISO format. """
    return time.strftime("%Y-%m-%d")

def group_by(iterable: Iterable[A], key_func: Callable[[A], B]) -> Dict[B, List[A]]:
    """ Groups an iterable by equality of keys. """
    out = dict() # type: Dict[B, List[A]]
    for item in iterable:
        key = key_func(item)
        if key in out:
            out[key].append(item)
        else:
            out[key] = [item]
    return out

def latest(reddit: Reddit) -> Result[str, Dict[str, Post]]:
    """ Get the latest posts """
    def get_number(post: Post) -> str: # pylint: disable=C0111
        return post.title.split()[2][1:]

    posts = list(reddit.subreddit('dailyprogrammer').new(limit=5))
    grouped = group_by(posts, get_number)
    full = [posts for posts in grouped.values() if len(posts) == 3]

    if empty(full):
        titles = [post.title for post in posts]
        return Err("Could not get matching challenges from: {}".format(titles))
    else:
        result = max(full, key=lambda posts: int(get_number(posts[0])))
        levels = {post.title.split()[3][1:-1] : post for post in result}
        return Ok(levels)

def choose_language(address: str, languages: List[str]) -> str:
    """ Chooses the language for this user.
        Uses the challenge number and email to seed the rng.
    """
    random.seed(address + get_date())
    return choose(languages)

def choose_level(users: Users) -> str:
    """ Chooses the level for this week based on a hash of the date """
    all_levels = [level
                  for levels in users.values()
                  for (level, languages) in levels.items()
                  for _ in languages]
    random.seed(get_date())
    return choose(sorted(all_levels))

def choose(elems: List[A]) -> A:
    """ Chooses a single element of the given list. """
    return elems[random.randrange(len(elems))]

def empty(xs: Iterable[A]) -> bool:
    """ Tests if an iterable is empty. """
    return not bool(xs)

def send_messages(users: Users, service: Any, levels: Dict[str, Post]) -> None:
    """ Send out messages to all the users. """
    level = choose_level(users)
    for (address, languages) in users.items():
        lang = None
        if empty(languages[level]):
            lang = "a language of your choice"
        else:
            lang = choose_language(address, languages[level])
        send_message(address, service, level, lang, levels[level])

def send_message(address: str, service: Any, level: str, language: str, post: Post) -> None:
    """ Sends the user a message containing the problem in the given post. """
    title = post.title.split(']')[-1].strip()
    date = get_date()
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
    without_newlines = message.replace("\n", "")
    print("Sending ({}, {}) to {}".format(level, language, address))
    if address == "tobinyehle@gmail.com":
        print(subject)
        print(without_newlines)
        send(service, "me", make_html_message(body=message,
                                              subject=subject,
                                              recipient=address))
