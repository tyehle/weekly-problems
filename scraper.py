""" Gets the weekly challenge from reddit.com/r/dailyprogrammer """

import sys
import json
import random
import time

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

def get_date():
    """ Gets the current date in the ISO format. """
    return time.strftime("%Y-%m-%d")

def latest(reddit):
    """ Get the latest posts """
    posts = list(reddit.subreddit('dailyprogrammer').new(limit=3))
    numbers = {post.title.split()[2][1:] for post in posts}
    if len(numbers) != 1:
        print("Challenge numbers do not match: {}".format([post.title for post in posts]))
        return None
    else:
        levels = {post.title.split()[3][1:-1] : post for post in posts}
        return levels

def choose_language(address, languages):
    """ Chooses the language for this user.
        Uses the challenge number and email to seed the rng.
    """
    random.seed(address + get_date())
    return choose(languages)

def choose_level(users):
    """ Chooses the level for this week based on a hash of the date """
    random.seed(get_date())
    return choose(["Easy", "Intermediate"])

def choose(elems):
    """ Chooses a single element of the given list. """
    return list(elems)[random.randrange(len(elems))]

def send_messages(users, yag, levels):
    """ Send out messages to all the users. """
    level = choose_level(users)
    for (address, languages) in users.items():
        lang = None
        if len(languages[level]) == 0:
            lang = "a language of your choice"
        else:
            lang = choose_language(address, languages[level])
        send_message(address, yag, level, lang, levels[level])

def send_message(address, yag, level, language, post):
    """ Sends the user a message containing the problem in the given post. """
    title = post.title.split(']')[-1].strip()
    date = get_date()
    subject = "[Weekly Programming Problem] {} in {}".format(title, language)
    message = """This week you will be doing the {} {} problem in {}!
                 To push your code to the studio repo (https://github.com/tyehle/programming-studio) put it in this week's folder in a folder with your name (ie: {}/tobin/*.py), or as a single file with your name in it (ie: {}/tobin_code.py).

                 This problem's was source is {}.

                 {}
                 """.format(level, title, language, date, date, post.shortlink, post.selftext_html)
    print("Sending ({}, {}) to {}".format(level, language, address))
    # if address == "tobinyehle@gmail.com":
    #     print(subject)
    #     print(message)
    yag.send(to=address, subject=subject, contents=message)

def main():
    """ Main function to run if this file is run as a script """
    reddit = init_reddit()
    if reddit is None:
        print("No reddit instance")
    else:
        with init_yag() as yag:
            levels = latest(reddit)
            if levels is None:
                print("Could not retrieve challenges")
            else:
                with open("users.json", "r") as user_file:
                    users = json.load(user_file)
                    if users is None:
                        print("Could not read user file")
                    else:
                        send_messages(users, yag, levels)
                        print("Messages sent")

if __name__ == "__main__":
    main()
