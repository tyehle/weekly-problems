""" Gets the weekly challenge from reddit.com/r/dailyprogrammer """

import sys
import random
import time
from typing import List, Dict, Callable, Iterable, TypeVar

import praw

from result import Result, Err, Ok
from jsonparse import run_parser_file, dict_parser, str_parser

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
C = TypeVar("C")

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

def empty(xs: Iterable[A]) -> bool:
    """ Tests if an iterable is empty. """
    return not bool(xs)

def latest(reddit: Reddit) -> Result[str, Dict[str, Post]]:
    """ Get the latest posts """
    def get_number(post: Post) -> int: # pylint: disable=C0111
        return int(post.title.split()[2][1:])

    def get_title(post: Post) -> str: # pylint: disable=C0111
        return post.title.split()[3][1:-1]

    posts = list(reddit.subreddit('dailyprogrammer').new(limit=11))
    grouped = group_by(posts, get_title)
    out = dict() # type: Dict[str, Post]

    for level in grouped.keys():
        if empty(grouped[level]):
            titles = [post.title for post in posts]
            return Err("No {} challenges in: {}".format(level, titles))
        else:
            out[level] = max(grouped[level], key=get_number)
    return Ok(out)

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
