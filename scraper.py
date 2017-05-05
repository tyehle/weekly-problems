""" Gets the weekly challenge from reddit.com/r/dailyprogrammer """

import sys
import json
import random
import time

from typing import List, Dict, Optional, Callable, Iterable, TypeVar

import praw
import yagmail

VERSION = "v0.1"
ID = "dailyprogrammer-scraper"
AUTHOR = "/u/ToboRoboLoco"

# Yag = yagmail.yagmail.SMTP
# Reddit = praw.reddit.Reddit
# Post = praw.models.reddit.submission.Submission
A = TypeVar("A")
B = TypeVar("B")

def user_agent() -> str:
    """ Build the user agent string """
    return "{}:{}:{} by {}".format(sys.platform, ID, VERSION, AUTHOR)

def init_reddit() -> Optional[praw.reddit.Reddit]:
    """ Gets a praw reddit instance """
    client_info = None
    with open("client-info.json", mode='r') as info_handle:
        client_info = json.load(info_handle)

    # why is error handling so silly

    if client_info is None:
        print("No client-info.json file found")
        return None
    else:
        return praw.Reddit(user_agent=user_agent(), **client_info)

def init_yag() -> yagmail.yagmail.SMTP:
    """ Gets a yagmail instance for sending emails. """
    yag = yagmail.SMTP("tobin.spam@gmail.com")
    yag.useralias = "robotobo@tobinyehle.com"
    return yag

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

def latest(reddit: praw.reddit.Reddit) -> Optional[Dict[str, praw.models.reddit.submission.Submission]]:
    """ Get the latest posts """
    posts = list(reddit.subreddit('dailyprogrammer').new(limit=5))
    grouped = group_by(posts, lambda post: post.title.split()[2][1:])
    only3 = filter(lambda posts: len(posts) == 3, grouped.values())
    result = max(only3,
                 key=lambda posts: int(posts[0].title.split()[2][1:]),
                 default=[])
    if len(result) != 3:
        print("Could not get matching challenges from: {}".format([post.title for post in posts]))
        return None
    else:
        levels = {post.title.split()[3][1:-1] : post for post in posts}
        return levels

def choose_language(address: str, languages: List[str]) -> str:
    """ Chooses the language for this user.
        Uses the challenge number and email to seed the rng.
    """
    random.seed(address + get_date())
    return choose(languages)

def choose_level(users: Dict[str, Dict[str, List[str]]]) -> str:
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

def send_messages(users: Dict[str, Dict[str, List[str]]], yag: yagmail.yagmail.SMTP, levels: Dict[str, praw.models.reddit.submission.Submission]) -> None:
    """ Send out messages to all the users. """
    level = choose_level(users)
    for (address, languages) in users.items():
        lang = None
        if len(languages[level]) == 0:
            lang = "a language of your choice"
        else:
            lang = choose_language(address, languages[level])
        send_message(address, yag, level, lang, levels[level])

def send_message(address: str, yag: yagmail.yagmail.SMTP, level: str, language: str, post: praw.models.reddit.submission.Submission) -> None:
    """ Sends the user a message containing the problem in the given post. """
    title = post.title.split(']')[-1].strip()
    date = get_date()
    subject = "[Weekly Programming Problem] {} in {}".format(title, language)
    push_instructions = ("To push your code to the studio repo "+
                         "(https://github.com/tyehle/programming-studio) put "+
                         "it in this week's folder in a folder with your name "+
                         "(ie: {date}/tobin/*.py), or as a single file with "+
                         "your name in it (ie: {date}/tobin_code.py)."
                        ).format(date=date)
    message = """This week you will be doing the {} {} problem in {}!
                 {}

                 This problem's source is {}.

                 {}
                 """.format(level, title, language,
                            push_instructions,
                            post.shortlink, post.selftext_html)
    print("Sending ({}, {}) to {}".format(level, language, address))
    # if address == "tobinyehle@gmail.com":
    #     print(subject)
    #     print(message)
    yag.send(to=address, subject=subject, contents=message)

def main() -> int:
    """ Main function to run if this file is run as a script """
    reddit = init_reddit()
    if reddit is None:
        print("No reddit instance")
        return 1

    with init_yag() as yag:
        levels = latest(reddit)
        if levels is None:
            print("Could not retrieve challenges")
            return 2

        with open("users.json", "r") as user_file:
            users = json.load(user_file)
            if users is None:
                print("Could not read user file")
                return 3

            send_messages(users, yag, levels)
            print("Messages sent")
            return 0

if __name__ == "__main__":
    exit(main())
