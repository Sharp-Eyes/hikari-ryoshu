"""Parser implementations for standard library and disnake enums and flags."""

import enum
import typing
import typing_extensions

import hikari.internal.enums as hikari_enum
from ryoshu.impl.parser import base as parser_base
from ryoshu.internal import aio

__all__: typing.Sequence[str] = ("EnumParser", "FlagParser")

_AnyEnum = typing.Union[enum.Enum, hikari_enum.Enum, hikari_enum.Flag]
_EnumT = typing.TypeVar("_EnumT", bound=_AnyEnum)


def _get_enum_type(enum_class: typing.Type[_AnyEnum]) -> typing.Optional[type]:
    if issubclass(enum_class, hikari_enum.Flag):
        return int

    maybe_type: type = getattr(enum_class, "_member_type_", object)
    if maybe_type is not object:
        return maybe_type

    # Get first member's type
    member_iter = iter(enum_class)
    maybe_type = typing.cast(  # python typing sucks.
        typing.Type[typing.Any], type(next(member_iter).value)
    )

    # If all members match this type, return it.
    if all(type(member.value) is maybe_type for member in member_iter):
        return maybe_type

    # No single type; store by name instead.
    return None


# Should have elevated priority so that e.g. Flag is prioritised over int.
@parser_base.register_parser_for(enum.Enum, hikari_enum.Enum, enum.Flag, hikari_enum.Flag, priority=10)
class EnumParser(parser_base.SourcedParser[_EnumT]):
    """Parser type for enums and flags.

    Enums and flags are stored by value instead of by name. This makes parsing
    a bit slower, but values are generally shorter than names.

    This parser type works for standard library and disnake enums and flags.
    Note that this only works for enums and flags where all values are of the
    same type.

    Parameters
    ----------
    enum_class:
        The enum or flag class to use for parsing.
    store_by_value:
        Whether :meth:`loads` and :meth:`dumps` expect the enum value type or a string.

        For enum types where the members are *not* all of the same type, this
        *must* be ``False``.

        For enum types where all members are integers, this defaults to
        ``True``, otherwise this defaults to ``False``.

    """

    enum_class: typing.Type[_EnumT]
    """The enum or flag class to use for parsing."""
    store_by_value: bool
    """Whether :meth:`loads` and :meth:`dumps` expect the enum's value type or a string.

    For enum types where the members are *not* all of the same type, this
    *must* be ``False``.
    """
    value_parser: parser_base.AnyParser
    """The parser responsible for converting to/from the enum type.

    If :attr:`store_by_values` is set to ``False``, this is *always* a
    :class:`~components.parser.StringParser`.
    """

    def __init__(
        self,
        enum_class: typing.Type[_EnumT],
        *,
        store_by_value: bool = True,
    ) -> None:
        value_type = _get_enum_type(enum_class)

        # If the value type could not be determined but the user explicitly set
        # store_by_value to True, raise an exception.
        if value_type is None:
            if store_by_value:
                message = (
                    "Cannot store enum members by value for enums with members of"
                    " varying types. Please either set `store_by_value` to False"
                    " or make sure all enum members are of the same type."
                )
                raise ValueError(message)
            
            value_type = str  # Store member names as strings.

        self.enum_class = enum_class
        self.store_by_value = store_by_value
        self.value_parser = parser_base.get_parser(value_type)

    @classmethod
    def default(cls, type_: type[_EnumT]) -> typing_extensions.Self:
        value_type = _get_enum_type(type_)
        return cls(type_, store_by_value=value_type is not None)

    async def loads(self, argument: str, *, source: object) -> _EnumT:
        """Load an enum member from a string.

        This uses the underlying :attr:`value_parser`.

        .. note::
            If :attr:`store_by_value` is True, the ``argument`` is expected to
            be the value of an enum member; otherwise, the ``argument`` is
            expted to be the name.

        Parameters
        ----------
        argument:
            The value that is to be loaded into a channel.

            This always matches the channel type of the parser.
        source:
            The source to use for parsing.

            If any of the inner parsers are sourced, this is automatically
            passed to them.

        """
        parsed = await parser_base.try_loads(self.value_parser, argument, source=source)

        if self.store_by_value:
            return self.enum_class(parsed)
        else:
            return self.enum_class[parsed]

    async def dumps(self, argument: _EnumT) -> str:
        """Dump an enum member into a string.

        .. note::
            If :attr:`store_by_value` is True, this dumps the name of the
            enum member passed as ``argument``; otherwise, this dumps its
            value.

        Parameters
        ----------
        argument:
            The value that is to be dumped.

        """
        if self.store_by_value:
            result = self.value_parser.dumps(argument.value)
        else:
            result = self.value_parser.dumps(argument.name)

        return await aio.eval_maybe_coro(result)


FlagParser = EnumParser