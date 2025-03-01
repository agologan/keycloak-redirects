from typing import TypeVar

T = TypeVar("T")


def unwrap(val: T | None) -> T:
    assert val is not None
    return val
