""" Module for loading json in a typesafe way. """

import json

from typing import Dict, List, Optional, Callable, TypeVar, Any, cast, Tuple

from result import Result, Err, Ok, map_m

# pylint: disable=C0103

A = TypeVar("A")
B = TypeVar("B")
# Generic type aliases need the new typing module
Parser = Callable[[Any], Result[str, A]]


def run_parser_file(filename: str, parser: "Parser[A]") -> Result[str, A]:
    """ Run a parser on the contents of a file. """
    try:
        with open(filename, mode="r") as handle:
            raw = handle.read()
            return run_parser(raw, parser)
    except OSError as exn:
        return Err(str(exn))


def run_parser(raw: str, parser: "Parser[A]") -> Result[str, A]:
    """ Run a parser on some raw string. """
    try:
        data = json.loads(raw)
        return parser(data)
    except ValueError as exn:
        return Err(str(exn))


def dict_parser(inner: "Parser[A]") -> "Parser[Dict[str, A]]":
    """ Parse a dictionary. """
    def parse_item(item: Tuple[Any, Any]) -> Result[str, Tuple[str, A]]:
        """Makes sure the key is a string, then parses the value"""
        key, value = item
        return str_parser(key).bind(lambda k: inner(value).fmap(lambda v: (k, v)))

    def out(obj: Any) -> Result[str, Dict[str, A]]: # pylint: disable=missing-docstring
        if isinstance(obj, dict):
            pairs = map_m(parse_item, obj.items()) # type: Result[str, List[Tuple[str, A]]]
            return pairs.fmap(lambda ps: {k: v for (k,v) in ps})
        else:
            return bad_type(dict, obj)

    return out


def list_parser(inner: "Parser[A]") -> "Parser[List[A]]":
    """ Parse a list. """
    def out(obj: Any) -> Result[str, List[A]]: # pylint: disable=missing-docstring
        if isinstance(obj, list):
            return map_m(inner, obj)
        else:
            return bad_type(list, obj)

    return out


def optional_parser(inner: "Parser[A]") -> "Parser[Optional[A]]":
    """ Parse an optional value.

    Args:
        inner: Parser to use if the object isn't None
    """
    def just(obj: A) -> Optional[A]:
        return obj

    def out(obj: Any) -> Result[str, Optional[A]]:
        if obj is None:
            return Ok(None)
        else:
            return inner(obj).fmap(just)

    return out


def field(name: str, parser: "Parser[A]", other_fields: Callable[[A], "Parser[B]"]) -> "Parser[B]":
    """Parse a field from an object.

    Any other fields should be parsed using a nested lambda. When all fields have been parsed the resulting data
    structure should be constructed using done.

    Example:
        >>> pair_parser = field("name", str_parser, lambda name:
        ...               field("number", int_parser, lambda number:
        ...               done((name, number))))
        >>> run_parser('{"name": "Bob", "number": 42}', pair_parser)
        Ok(('Bob', 42))

    Args:
        name: The name of the field to parse
        parser: The parser to use on the field
        other_fields: Any other fields to parse

    Returns:
        An object parser
    """
    def out(obj: Any) -> Result[str, B]:
        """The parser to return"""
        if isinstance(obj, dict):
            if name in obj:
                return parser(obj[name]).bind(lambda parsed: other_fields(parsed)(obj))
            else:
                return Err("Missing field {} in {}".format(name, obj))
        else:
            return bad_type(dict, obj)

    return out


def done(result: A) -> "Parser[A]":
    """Finish parsing an object.

    Constructs a parser that always succeeds by throwing away its argument and returning result instead.

    Args:
        result: The result of parsing

    Returns:
        A parser that always returns result
    """
    def parser(_: Any) -> Result[str, A]:
        """The constant parser"""
        return Ok(result)

    return parser


def bad_type(expected: Any, result: Any) -> Result[str, A]:
    """ Fail with a type error message. """
    return Err("Expecting {}, but got {} in '{}'".format(expected, result.__class__, result))


def leaf_parser(t: type) -> Parser:
    """ Generic parser for json leaves. """
    def parser(obj: Any) -> Result[str, Any]: # pylint: disable=missing-docstring
        if isinstance(obj, t):
            return Ok(obj)
        else:
            return bad_type(t, obj)

    return parser


str_parser = leaf_parser(str) # type: Parser[str]
int_parser = leaf_parser(int) # type: Parser[int]
float_parser = leaf_parser(float) # type: Parser[float]
bool_parser = leaf_parser(bool) # type: Parser[bool]


def none_parser(obj: Any) -> Result[str, None]:
    """ Parse none. """
    if obj is None:
        return Ok(obj)
    else:
        return bad_type(None, obj)
