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
STATE_PATH = "users.json"


class User(object):
    """A user in the system.

    Attributes:
        address: The user's email address
        langs: The set of languages the user has specified
        vetoed: If the user has vetoed this week's challenge
        last_lang: The last language the user was assigned
    """
    def __init__(self,
                 address: str,
                 langs: Dict[str, List[str]],
                 vetoed: bool,
                 last_lang: Optional[str]
                 ) -> None:
        """Populates all the fields of a new user.

        Args:
            address: The user's email address
            langs: The set of languages the user has specified
            vetoed: If the user has vetoed this week's challenge
            last_lang: The last language the user was assigned
        """
        self.address = address
        self.langs = langs
        self.vetoed = vetoed
        self.last_lang = last_lang

    def __repr__(self) -> str:
        """String representation of the user."""
        return "User(address={}, langs={}, vetoed={}, last_lang={})".format(
            repr(self.address),
            repr(self.langs),
            repr(self.vetoed),
            repr(self.last_lang)
        )


def load_state() -> Result[str, List[User]]:
    """Load the list of users from disk.

    Returns:
        The list of users on the disk, or Err if there was a problem during loading.
    """
    user_parser = field("address", str_parser, lambda address:
                  field("langs", dict_parser(list_parser(str_parser)), lambda langs:
                  field("vetoed", bool_parser, lambda vetoed:
                  field("last_lang", optional_parser(str_parser), lambda last_lang:
                  done(User(address, langs, vetoed, last_lang))))))
    return run_parser_file(STATE_PATH, list_parser(user_parser))


def save_state(users: List[User]) -> None:
    """Saves a list of users to disk, overwriting the any data currently stored.

    Args:
        users: The list of users to write
    """
    json.dump([user.__dict__ for user in users], open(STATE_PATH, "w"), indent=2)
