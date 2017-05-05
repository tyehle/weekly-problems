class Submission:
    @property
    def shortlink(self) -> str: ...

    # These are added by calling setattr on everything in _data in RedditBase
    title = ... # type: str
    selftext_html = ... # type: str
