"""Implementation of parser base classes upon which actual parsers are built."""

from __future__ import annotations

import typing

from ryoshu.api import parser as parser_api
from ryoshu.internal import aio

if typing.TYPE_CHECKING:
    import typing_extensions

__all__: typing.Sequence[str] = (
    "register_parser",
    "get_parser",
    "Parser",
    "SourcedParser",
)

_PARSERS: dict[type[typing.Any], type[AnyParser]] = {}
_REV_PARSERS: dict[type[AnyParser], tuple[type, ...]] = {}
_PARSER_PRIORITY: dict[type[AnyParser], int] = {}


def register_parser(
    parser: typing.Type[ParserWithArgumentType[parser_api.ParserType]],
    *types: typing.Type[parser_api.ParserType],
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


def _issubclass(
    cls: type, class_or_tuple: typing.Union[type, typing.Tuple[type, ...]]
) -> bool:
    try:
        return issubclass(cls, class_or_tuple)

    except TypeError:
        if isinstance(class_or_tuple, tuple):
            return any(cls is cls_ for cls_ in class_or_tuple)

        return cls is class_or_tuple


def _get_parser_type(type_: type[parser_api.ParserType]) -> type[ParserWithArgumentType[parser_api.ParserType]]:
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
def get_parser(type_: type[parser_api.ParserType]) -> ParserWithArgumentType[parser_api.ParserType]:
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

def is_sourced(
    parser: ParserWithArgumentType[parser_api.ParserType],
) -> typing_extensions.TypeIs[SourcedParser[parser_api.ParserType]]:
    """Typeguard function to check whether a parser is sourced."""
    return parser.is_sourced


async def try_loads(
    parser: ParserWithArgumentType[parser_api.ParserType],
    argument: str,
    *,
    source: typing.Optional[object] = None,
) -> parser_api.ParserType:
    return await aio.eval_maybe_coro(
        parser.loads(argument, source=source)
        if is_sourced(parser)
        else parser.loads(argument)
    )


class _ParserBase(typing.Protocol[parser_api.ParserType]):
    # def __init__(self, *args: object, **kwargs: object) -> None:
    #     super().__init__(*args, **kwargs)

    @classmethod
    def default(cls, type_: type[parser_api.ParserType]) -> typing_extensions.Self:
        """Return the default implementation of this parser type.

        By default, this will just create the parser class with no arguments,
        but this can be overwritten on child classes for customised behaviour.

        Returns
        -------
        Parser:
            The default parser instance for this parser type.

        """
        return cls()

    def dumps(self, argument: parser_api.ParserType, /) -> aio.MaybeCoroutine[str]:
        # <<Docstring inherited from parser_api.Parser>>
        ...


@typing.runtime_checkable
class Parser(
    _ParserBase[parser_api.ParserType],
    parser_api.Parser[parser_api.ParserType],
    typing.Protocol[parser_api.ParserType],
):
    """Class that handles parsing of one custom id field to and from a desired type.

    A parser contains two main methods, :meth:`loads` and :meth:`dumps`.
    ``loads``, like :func:`json.loads` serves to turn a string value into
    a different type. Similarly, ``dumps`` serves to convert that type
    back into a string.
    """

    is_sourced: typing.ClassVar[typing.Literal[False]] = False

    def loads(  # noqa: D102
        self, argument: typing.Any, /  # noqa: ANN401
    ) -> aio.MaybeCoroutine[parser_api.ParserType]:
        # <<Docstring inherited from parser_api.Parser>>
        ...


@typing.runtime_checkable
class SourcedParser(
    _ParserBase[parser_api.ParserType],
    parser_api.SourcedParser[parser_api.ParserType, parser_api.SourceType],
    typing.Protocol[parser_api.ParserType, parser_api.SourceType],
):
    """Class that handles parsing of one custom id field to and from a desired type.

    A parser contains two main methods, :meth:`loads` and :meth:`dumps`.
    ``loads``, like :func:`json.loads` serves to turn a string value into
    a different type. Similarly, ``dumps`` serves to convert that type
    back into a string.
    """

    is_sourced: typing.ClassVar[typing.Literal[True]] = True

    def loads(  # noqa: D102
        self,
        argument: typing.Any,  # noqa: ANN401
        /,
        *,
        source: parser_api.SourceType,
    ) -> aio.MaybeCoroutine[parser_api.ParserType]:
        # <<Docstring inherited from parser_api.Parser>>
        ...


ParserWithArgumentType: typing_extensions.TypeAlias = typing.Union[
    Parser[parser_api.ParserType],
    SourcedParser[parser_api.ParserType, typing.Any],
]
AnyParser: typing_extensions.TypeAlias = ParserWithArgumentType[typing.Any]
AnyParserT = typing.TypeVar("AnyParserT", bound=AnyParser)
