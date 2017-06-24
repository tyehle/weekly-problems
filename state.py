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
        langs: The set of languages the user has specified
        vetoed: If the user has vetoed this week's challenge
        last_lang: The last language the user was assigned
    """
    def __init__(self,
                 langs: Dict[str, List[str]],
                 vetoed: bool,
                 last_lang: Optional[str]
                ) -> None:
        """Populates all the fields of a new user.

        Args:
            langs: The set of languages the user has specified
            vetoed: If the user has vetoed this week's challenge
            last_lang: The last language the user was assigned
        """
        self.langs = langs
        self.vetoed = vetoed
        self.last_lang = last_lang

    def __repr__(self) -> str:
        """String representation of the user."""
        return "User(langs={}, vetoed={}, last_lang={})".format(
            repr(self.langs),
            repr(self.vetoed),
            repr(self.last_lang)
        )


def load_state() -> Result[str, Dict[str, User]]:
    """Load the users from disk.

    Returns:
        A map from email address to the user, or an Err if there was a problem during loading.
    """
    user_parser = field("langs", dict_parser(list_parser(str_parser)), lambda langs:
                  field("vetoed", bool_parser, lambda vetoed:
                  field("last_lang", optional_parser(str_parser), lambda last_lang:
                  done(User(langs, vetoed, last_lang))))) # pylint: disable=undefined-variable
    return run_parser_file(STATE_PATH, dict_parser(user_parser))


def save_state(users: Dict[str, User]) -> None:
    """Saves a map of addresses to users to disk, overwriting any data currently stored.

    Args:
        users: The map of users to write
    """
    raw = {address: user.__dict__ for (address, user) in users.items()}
    json.dump(raw, open(STATE_PATH, "w"), indent=2)
