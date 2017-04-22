""" Gets the weekly challenge from reddit.com/r/dailyprogrammer """

import sys
import json
import praw

VERSION = "v0.1"
ID = "dailyprogrammer-scraper"
AUTHOR = "/u/ToboRoboLoco"

def user_agent():
    """ Build the user agent string """
    return "{}:{}:{} by {}".format(sys.platform, ID, VERSION, AUTHOR)

def init_instance():
    """ Gets a praw reddit instance """
    client_info = None
    with open("client-info", mode='r') as info_handle:
        client_info = json.load(info_handle)

    # why is error handling so silly

    if client_info is None:
        print("No client-info file found")
        return None
    else:
        return praw.Reddit(user_agent=user_agent(), **client_info)

def main():
    """ Main function to run if this file is run as a script """
    reddit = init_instance()
    if reddit is None:
        print("No reddit instance")
    else:
        for submission in reddit.subreddit('dailyprogrammer').new(limit=6):
            print(submission.title)

if __name__ == "__main__":
    main()
