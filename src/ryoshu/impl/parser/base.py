"""Implementation of parser base classes upon which actual parsers are built."""

from __future__ import annotations

import abc
import typing

import typing_extensions

from ryoshu.api import parser as parser_api

if typing.TYPE_CHECKING:
    from ryoshu.internal import aio

__all__: typing.Sequence[str] = (
    "register_parser",
    "get_parser",
    "Parser",
)

AnyParser: typing_extensions.TypeAlias = "Parser[typing.Any]"
AnyParserT = typing.TypeVar("AnyParserT", bound=AnyParser)

_PARSERS: dict[type[typing.Any], type[AnyParser]] = {}
_REV_PARSERS: dict[type[AnyParser], tuple[type, ...]] = {}
_PARSER_PRIORITY: dict[type[AnyParser], int] = {}


def register_parser(
    parser: type[Parser[parser_api.ParserType]],
    *types: type[parser_api.ParserType],
    priority: int = 0,
    force: bool = True,
) -> None:
    """Register a parser class as the default parser for the provided type.

    The default parser will automatically be used for any field annotated
    with that type. For example, the default parser for integers is
    :class:`components.IntParser`, an instance of which will automatically be
    assigned to any custom id fields annotated with `int`.

    Parameters
    ----------
    parser:
        The parser to register.
    *types:
        The types for which to register the provided parser as the default.
    force:
        Whether or not to overwrite existing defaults. Defaults to ``True``.

    """
    # This allows e.g. is_default_for=(Tuple[Any, ...],) so pyright doesn't complain.
    # The stored type will then still be tuple, as intended.
    types = tuple(typing.get_origin(type_) or type_ for type_ in types)
    setter = dict.__setitem__ if force else dict.setdefault  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    setter(_REV_PARSERS, parser, types)
    setter(_PARSER_PRIORITY, parser, priority)
    for type_ in types:
            setter(_PARSERS, type_, parser)


def register_parser_for(
    *is_default_for: type[typing.Any],
    priority: int = 0,
) -> typing.Callable[[type[AnyParserT]], type[AnyParserT]]:

    def wrapper(cls: type[AnyParserT]) -> type[AnyParserT]:
        register_parser(cls, *is_default_for, priority=priority)
        return cls

    return wrapper


def _issubclass(cls: type, class_or_tuple: type | tuple[type, ...]) -> bool:
    try:
        return issubclass(cls, class_or_tuple)

    except TypeError:
        if isinstance(class_or_tuple, tuple):
            return any(cls is cls_ for cls_ in class_or_tuple)

        return cls is class_or_tuple


def _get_parser_type(type_: type[parser_api.ParserType]) -> type[Parser[parser_api.ParserType]]:
    # Fast lookup...
    if type_ in _PARSERS:
        return _PARSERS[type_]

    # Slow lookup for subclasses of existing types...
    best_entry = max(
        (entry for entry, parser_types in _REV_PARSERS.items() if _issubclass(type_, parser_types)),
        default=None,
        key=_PARSER_PRIORITY.__getitem__,
    )
    if best_entry is not None:
        return best_entry

    message = f"No parser available for type {type_.__name__!r}."
    raise TypeError(message)


# TODO: Maybe cache this?
def get_parser(type_: type[parser_api.ParserType]) -> Parser[parser_api.ParserType]:
    r"""Get the default parser for the provided type.

    Note that type annotations such as ``Union[int, str]`` are also valid.

    Parameters
    ----------
    type\_:
        The type for which to return the default parser.

    Returns
    -------
    :class:`Parser`\[``_T``]:
        The default parser for the provided type.

    Raises
    ------
    :class:`TypeError`:
        Could not create a parser for the provided type.

    """
    origin = typing.get_origin(type_)
    return _get_parser_type(origin or type_).default(type_)


class Parser(parser_api.Parser[parser_api.ParserType], abc.ABC):
    """Class that handles parsing of one custom id field to and from a desired type.

    A parser contains two main methods, :meth:`loads` and :meth:`dumps`.
    ``loads``, like :func:`json.loads` serves to turn a string value into
    a different type. Similarly, ``dumps`` serves to convert that type
    back into a string.
    """

    @classmethod
    def default(cls, type_: type[parser_api.ParserType], /) -> typing_extensions.Self:  # noqa: ARG003
        # <<Docstring inherited from parser_api.Parser>>
        return cls()

    def loads(
        self, argument: typing.Any, /,  # noqa: ANN401
    ) -> aio.MaybeCoroutine[parser_api.ParserType]:
        # <<Docstring inherited from parser_api.Parser>>
        ...

    def dumps(self, argument: parser_api.ParserType, /) -> aio.MaybeCoroutine[str]:
        # <<Docstring inherited from parser_api.Parser>>
        ...
