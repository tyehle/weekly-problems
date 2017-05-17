""" A result type like in rust. """

from typing import TypeVar, Generic, Callable, Union, Any, List, Iterable, cast

E = TypeVar("E")
T = TypeVar("T")
A = TypeVar("A")

class Result(Generic[E, T]):
    """ Result super class. Do NOT construct an instance of this by hand.
        Instead use Ok, or Err.
    """
    def __init__(self, is_ok: bool, value: Union[E, T]) -> None:
        self._value = value
        self.is_ok = is_ok
        self.is_err = not is_ok

    def extract(self, err_func: Callable[[E], A], ok_func: Callable[[T], A]) -> A:
        """Map both values to a single type. """
        if self.is_ok:
            return ok_func(cast(T, self._value))
        else:
            return err_func(cast(E, self._value))

    def fmap(self, func: Callable[[T], A]) -> "Result[E, A]":
        """ Functor map maps ok values, and leaves err values as is. """
        return self.extract(Err, lambda ok: Ok(func(ok)))

    def bind(self, cont: Callable[[T], "Result[E, A]"]) -> "Result[E, A]":
        """ Chains another failing computation onto this one. """
        return self.extract(Err, cont)

    def __add__(self, cont: Callable[[T], "Result[E, A]"]) -> "Result[E, A]":
        """ A Synonym for bind. """
        return self.bind(cont)

    def map_err(self, func: Callable[[E], A]) -> "Result[A, T]":
        """ Maps an err value and leaves an ok value as is. """
        return self.extract(lambda err: Err(func(err)), Ok)

    def map_ok(self, func: Callable[[T], A]) -> "Result[E, A]":
        """ Maps an ok value and leaves an err value as is. """
        return self.fmap(func)

def from_exception(func: Callable[..., A],
                   ex: Any,
                   mapping: Callable[[Any], E]) -> Callable[..., Result[E, A]]:
    """ Makes a version of the given function that returns a result type
        instead of throwing the given exception.
    """
    def inner(*args: Any, **kwargs: Any) -> Result[E, A]: # pylint: disable=C0111
        try:
            return Ok(func(*args, **kwargs))
        except ex as failure:
            return Err(mapping(failure))
    return inner

def lift(func: Callable[[A], T]) -> Callable[[A], Result[E, T]]:
    """ Lift a regular function to return a result. """
    return lambda arg: Ok(func(arg))
    def inner(arg: A) -> Result[E, T]:
        return Ok(func(arg))
    return inner

def pure(value: T) -> Result[E, T]:
    """ Puts a regular value into a result context. Synonym of Ok. """
    return Ok(value)

def map_m(func: Callable[[A], Result[E, T]], items: Iterable[A]) -> Result[E, List[T]]:
    """ Iterate over some input, returning a list of good results, or the first
        failure.
    """
    out = pure([]) # type: Result[E, List[T]]
    for item in items:
        out = out.bind(lambda done: func(item).fmap(lambda mapped: done + [mapped]))
    return out

class Ok(Result[E, T]): # pylint: disable=R0903
    """ A result representing success. """
    def __init__(self, value: T) -> None:
        super().__init__(True, value)

    def __repr__(self) -> str:
        return "Ok({})".format(repr(self._value))

class Err(Result[E, T]): # pylint: disable=R0903
    """ A result representing failure. """
    def __init__(self, value: E) -> None:
        super().__init__(False, value)

    def __repr__(self) -> str:
        return "Err({})".format(repr(self._value))
