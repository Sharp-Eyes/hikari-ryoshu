"""Protocols for parser types."""

import typing

import typing_extensions

from ryoshu.internal import aio

__all__: typing.Sequence[str] = ("Parser",)


ParserType = typing_extensions.TypeVar(
    "ParserType",
    default=typing.Any,
    infer_variance=True,
)
"""A typevar denoting the type of the parser.

A parser of a given type takes (any subclass of) that type as argument to
:meth:`.Parser.dumps`, and returns (any subclass of) that type from
:meth:`.Parser.loads`.
"""

SourceType = typing_extensions.TypeVar(
    "SourceType",
    default=typing.Any,
    infer_variance=True,
)
"""A typevar denoting the source type of the parser.

The source type denotes the *minumum requirement* for a parser to load a string
into its :obj:`ParserType`.
"""


class Parser(typing.Protocol[ParserType]):
    """The baseline protocol for any kind of parser.

    Any and all parser types must implement this protocol in order to be
    properly handled by Ryoshu.
    """

    __slots__: typing.Sequence[str] = ()

    def loads(self, argument: str, /) -> aio.MaybeCoroutine[ParserType]:
        r"""Load a value from a string and apply the necessary conversion logic.

        Any errors raised inside this method remain unmodified, and should be
        handled externally.

        .. note::
            This method can be either sync or async.

        Parameters
        ----------
        argument:
            The argument to parse into the desired type.

        Returns
        -------
        :data:`.ParserType`:
            In case the parser method was sync, the parsed result is returned
            as-is.
        :class:`~typing.Coroutine`\[:data:`.ParserType`]:
            In case the parser method was async, the parser naturally returns a
            coroutine. Awaiting this coroutine returns the parser result.

        """
        ...

    def dumps(self, argument: ParserType, /) -> aio.MaybeCoroutine[str]:
        r"""Dump a value from a given type and convert it to a string.

        In most cases it is imperative to ensure that this is done in a
        reversible way, such that calling :meth:`loads` on the result of this
        function returns the original input. For example:

        .. code-block:: python3

            >>> parser = IntParser()
            >>> input_str = "1"
            >>> parsed_int = parser.loads(input_str)
            >>> dumped_int = parser.dumps(parsed_int)
            >>> input_str == dumped_int
            True

        Any errors raised inside this method remain unmodified, and should be
        handled externally.

        .. note::
            This method can be either sync or async.

        Parameters
        ----------
        argument:
            The argument to parse into the desired type.

        Returns
        -------
        :class:`str`:
            In case the parser method was sync, the resulting dumped argument.
        :class:`~typing.Coroutine`\[:class:`str`]:
            In case the parser method was async, the parser naturally returns a
            coroutine. Awaiting this coroutine returns the dumped argument.

        """
        ...


class SourcedParser(typing.Protocol[ParserType, SourceType]):
    """The baseline protocol for any kind of sourced parser.

    A sourced parser is a parser that needs some kind of state to be able to
    parse its value. For example, a parser that needs to access an interaction
    object to get its author would be a sourced parser.

    Any and all parser types must implement this protocol in order to be
    properly handled by Ryoshu.
    """

    __slots__: typing.Sequence[str] = ()

    def loads(
        self,
        argument: str,
        /,
        *,
        source: SourceType,
    ) -> aio.MaybeCoroutine[ParserType]:
        r"""Load a value from a string and apply the necessary conversion logic.

        Any errors raised inside this method remain unmodified, and should be
        handled externally.

        .. note::
            This method can be either sync or async.

        Parameters
        ----------
        argument:
            The argument to parse into the desired type.
        source:
            The source object with which the argument should be parsed. For
            example, parsing a :class:`disnake.Member` uses the source to
            determine the guild from which the member should be derived.
            In this case, the source should be any object that defines
            ``.guild``.

        Returns
        -------
        :data:`.ParserType`:
            In case the parser method was sync, the parsed result is returned
            as-is.
        :class:`~typing.Coroutine`\[:data:`.ParserType`]:
            In case the parser method was async, the parser naturally returns a
            coroutine. Awaiting this coroutine returns the parser result.

        """
        ...

    def dumps(self, argument: ParserType, /) -> aio.MaybeCoroutine[str]:
        r"""Dump a value from a given type and convert it to a string.

        In most cases it is imperative to ensure that this is done in a
        reversible way, such that calling :meth:`loads` on the result of this
        function returns the original input. For example:

        .. code-block:: python3

            >>> parser = IntParser()
            >>> input_str = "1"
            >>> parsed_int = parser.loads(input_str)
            >>> dumped_int = parser.dumps(parsed_int)
            >>> input_str == dumped_int
            True

        Any errors raised inside this method remain unmodified, and should be
        handled externally.

        .. note::
            This method can be either sync or async.

        Parameters
        ----------
        argument:
            The argument to parse into the desired type.

        Returns
        -------
        :class:`str`:
            In case the parser method was sync, the resulting dumped argument.
        :class:`~typing.Coroutine`\[:class:`str`]:
            In case the parser method was async, the parser naturally returns a
            coroutine. Awaiting this coroutine returns the dumped argument.

        """
        ...


ParserWithArgumentType: typing_extensions.TypeAlias = typing.Union[
    Parser[ParserType], SourcedParser[ParserType, typing.Any],
]
AnyParser: typing_extensions.TypeAlias = ParserWithArgumentType[typing.Any]
