""" Gets the weekly challenge from reddit.com/r/dailyprogrammer """

import sys
import json
import random

import praw
import yagmail

VERSION = "v0.1"
ID = "dailyprogrammer-scraper"
AUTHOR = "/u/ToboRoboLoco"

def user_agent():
    """ Build the user agent string """
    return "{}:{}:{} by {}".format(sys.platform, ID, VERSION, AUTHOR)

def init_reddit():
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

def init_yag():
    """ Gets a yagmail instance for sending emails. """
    yag = yagmail.SMTP("tobin.spam@gmail.com")
    yag.useralias = "robotobo@tobinyehle.com"
    return yag

def latest(reddit):
    """ Get the latest posts """
    posts = list(reddit.subreddit('dailyprogrammer').new(limit=3))
    numbers = {post.title.split()[2][1:] for post in posts}
    if len(numbers) != 1:
        print("Challenge numbers do not match: {}".format([post.title for post in posts]))
        return None
    else:
        number = numbers.pop()
        levels = {post.title.split()[3][1:-1] : post for post in posts}
        return (levels, number)

def choose_language(address, languages, number):
    """ Chooses the language for this user.
        Uses the challenge number and email to seed the rng.
    """
    levels = sorted(languages.keys())
    all_languages = sorted({l for ls in languages.values() for l in ls})
    lang_to_level = [(lang, [l for l in levels if lang in languages[l]])
                     for lang in all_languages]
    # don't even thing about doing this concurrently
    random.seed(address + number)
    pair = choose(lang_to_level)
    level = choose(pair[1])
    return (pair[0], level)

def choose(elems):
    """ Chooses a single element of the given list. """
    return list(elems)[random.randrange(len(elems))]

def send_messages(users, yag, levels, number):
    """ Send out messages to all the users. """
    for (address, languages) in users.items():
        (lang, level) = choose_language(address, languages, number)
        send_message(address, yag, level, lang, levels[level])

def send_message(address, yag, level, language, post):
    """ Sends the user a message containing the problem in the given post. """
    message = """This week you will be doing a problem rated {} in {}!

                 This problem's was source is {}.

                 {}
                 """.format(level, language, post.shortlink, post.selftext_html)
    print("Sending to {}: {}".format(address, message))
    if address == "tobinyehle@gmail.com":
        yag.send(to=address, subject="Weekly Programming Problem", contents=message)

def main():
    """ Main function to run if this file is run as a script """
    reddit = init_reddit()
    if reddit is None:
        print("No reddit instance")
    else:
        with init_yag() as yag:
            late = latest(reddit)
            if late is None:
                print("Could not retrieve challenges")
            else:
                (levels, number) = late
                with open("users.json", "r") as user_file:
                    users = json.load(user_file)
                    if users is None:
                        print("Could not read user file")
                    else:
                        send_messages(users, yag, levels, number)
                        print("Messages sent")

if __name__ == "__main__":
    main()
