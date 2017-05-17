""" Module for loading json in a typesafe way. """

import json

from typing import Dict, List, Callable, TypeVar, Any, cast, Tuple

from result import Result, Err, Ok, map_m

# pylint: disable=C0103

A = TypeVar("A")
# Generic type aliases need the new typing module
# Parser = Callable[[Any], Result[str, A]]

def run_parser(raw: str, parser: Callable[[Any], Result[str, A]]) -> Result[str, A]:
    """ Run a parser on some raw string. """
    try:
        data = json.loads(raw)
        return parser(data)
    except json.decoder.JSONDecodeError as exn:
        return Err(str(exn))

def dict_parser(obj: Any,
                inner_parser: Callable[[Any], Result[str, A]]) -> Result[str, Dict[str, A]]:
    """ Parse a dictionary. """
    def check_item(item: Tuple[Any, Any]) -> Result[str, A]: # pylint: disable=C0111
        key, value = item
        return str_parser(key).bind(lambda _: inner_parser(value))

    if isinstance(obj, dict):
        return map_m(check_item, obj.items()).fmap(lambda _: cast(Dict[str, A], obj))
    else:
        return bad_type(dict, obj)

def list_parser(obj: Any,
                inner_parser: Callable[[Any], Result[str, A]]) -> Result[str, List[A]]:
    """ Parse a list. """
    if isinstance(obj, list):
        return map_m(inner_parser, obj)
    else:
        return bad_type(list, obj)

def bad_type(expected: Any, result: Any) -> Result[str, A]:
    """ Fail with a type error message. """
    return Err("Expecting {}, but got {} in '{}'".format(expected, result.__class__, result))

def leaf_parser(t: type) -> Callable[[Any], Result[str, A]]:
    """ Generic parser for json leaves. """
    def parser(obj: Any) -> Result[str, A]: # pylint: disable=C0111
        if isinstance(obj, t):
            return Ok(cast(A, obj))
        else:
            return bad_type(t, obj)
    return parser

str_parser = leaf_parser(str) # type: Callable[[Any], Result[str, str]]
int_parser = leaf_parser(int) # type: Callable[[Any], Result[str, int]]
float_parser = leaf_parser(float) # type: Callable[[Any], Result[str, float]]
bool_parser = leaf_parser(bool) # type: Callable[[Any], Result[str, bool]]

def none_parser(obj: Any) -> Result[str, None]:
    """ Parse none. """
    if obj is None:
        return Ok(obj)
    else:
        return bad_type(None, obj)
