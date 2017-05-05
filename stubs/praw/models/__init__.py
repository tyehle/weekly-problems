from .reddit.multi import Subreddit

class SubredditHelper:
    def __call__(self, display_name: str) -> Subreddit: ...
