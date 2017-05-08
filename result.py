""" A result type like in rust """

from typing import TypeVar, Generic, Callable, Union, cast

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
        """ Map both values to a single type. """
        if self.is_ok:
            return ok_func(cast(T, self._value))
        else:
            return err_func(cast(E, self._value))

    def map_err(self, func: Callable[[E], A]) -> Result[A, T]:
        return self.extract(lambda err: Err(func(err)), Ok)

    def map_ok(self, func: Callable[[T], A]) -> Result [E, A]:
        return self.extract(Err, lambda ok: Ok(func(ok)))

class Ok(Result[E, T]):
    def __init__(self, value: T) -> None:
        super(True, value)

class Err(Result[E, T]):
    def __init__(self, value: E) -> None:
        super(False, value)
