"""Ports the user state to the new version"""

from mypy_extensions import NoReturn

from jsonparse import dict_parser, list_parser, str_parser, run_parser_file
from user import User, save_users


def throw(exn: BaseException) -> NoReturn:
    """Turn raise into an expression"""
    raise exn


def main(path: str) -> None:
    """Main function to run if this file is run as a script"""
    old_parser = dict_parser(dict_parser(list_parser(str_parser)))
    parsed_users = run_parser_file(path, old_parser)
    users = parsed_users.extract(
        err_func=lambda err: throw(RuntimeError("Could not parse users: {}".format(err))),
        ok_func=lambda u: u
    )
    save_users({address: User(langs, vetoed=False, last_lang=None, last_level=None)
                for address, langs in users.items()})

if __name__ == "__main__":
    main("users.json")
