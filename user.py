"""
Module containing data structures for internal state as well as functions for
reading and writing the state.
"""

from typing import Dict, List, Optional
import json

from jsonparse import (
    run_parser_file,
    field,
    done,
    str_parser,
    dict_parser,
    list_parser,
    bool_parser,
    optional_parser
)
from result import Result


# Path to the file where user data is stored
PATH = "users.json"


class User(object): # pylint: disable=too-few-public-methods
    """A user in the system.

    Attributes:
        langs: The set of languages the user has specified
        vetoed: If the user has vetoed this week's challenge
        last_lang: The last language the user was assigned
        last_level: The last level that was mailed out
    """
    def __init__(self,
                 langs: Dict[str, List[str]],
                 vetoed: bool,
                 last_lang: Optional[str],
                 last_level: Optional[str]
                ) -> None:
        """Populates all the fields of a new user.

        Args:
            langs: The set of languages the user has specified
            vetoed: If the user has vetoed this week's challenge
            last_lang: The last language the user was assigned
            last_level: The last level that was mailed out
        """
        self.langs = langs
        self.vetoed = vetoed
        self.last_lang = last_lang
        self.last_level = last_level

    def __repr__(self) -> str:
        """String representation of the user."""
        return "User(langs={}, vetoed={}, last_lang={}, last_level={})".format(
            repr(self.langs),
            repr(self.vetoed),
            repr(self.last_lang),
            repr(self.last_level)
        )


def load_users() -> Result[str, Dict[str, User]]:
    """Load the users from disk.

    Returns:
        A map from email address to the user, or an Err if there was a problem during loading.
    """
    # pylint: disable=bad-continuation
    user_parser = field("langs", dict_parser(list_parser(str_parser)), lambda langs:
                  field("vetoed", bool_parser, lambda vetoed:
                  field("last_lang", optional_parser(str_parser), lambda last_lang:
                  field("last_level", optional_parser(str_parser), lambda last_level:
                  done(User(langs, vetoed, last_lang, last_level)))))) # pylint: disable=undefined-variable
    # pylint: enable=bad-continuation
    return run_parser_file(PATH, dict_parser(user_parser))


def save_users(users: Dict[str, User]) -> None:
    """Saves a map of addresses to users to disk, overwriting any data currently stored.

    Args:
        users: The map of users to write
    """
    raw = {address: user.__dict__ for (address, user) in users.items()}
    json.dump(raw, open(PATH, "w"), indent=2)
