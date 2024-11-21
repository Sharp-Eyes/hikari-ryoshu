import contextlib
import contextvars
import typing

_T = typing.TypeVar("_T")


@contextlib.contextmanager
def wrap(contextvar: contextvars.ContextVar[_T], value: _T) -> typing.Generator[None, None, None]:
    token = contextvar.set(value)
    try:
        yield

    finally:
        contextvar.reset(token)
