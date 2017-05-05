from typing import Any, Generic, TypeVar

from .generator import ListingGenerator
from ..reddit.submission import Submission

A = TypeVar("A")

class BaseListingMixin(Generic[A]):
    def new(self, **generator_kwargs: Any) -> ListingGenerator[A]: ...

class SubredditListingMixin(BaseListingMixin[Submission]):
    ...
