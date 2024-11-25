"""Field implementations extending :func:`attrs.field`."""

import enum
import typing

import attrs
import typing_extensions

from ryoshu.api import parser as parser_api

__all__: typing.Sequence[str] = ("field",)


_T = typing_extensions.TypeVar("_T", default=typing.Any)


# Workaround and re-export for attrs typing.
import attr._make  # noqa: E402

NothingType: typing_extensions.TypeAlias = attr._make._Nothing  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
NOTHING = attr._make._Nothing.NOTHING  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001


class FieldMetadata(str, enum.Enum):
    """Enum containing keys for field metadata."""

    PARSER = 0
    """Metadata key to store parser information."""
    FIELDTYPE = 1
    """Metadata key to store field type information. See :class:`FieldType`."""


class FieldType(enum.Flag):
    """Flag containing field metadata values for the field type.

    Note that a field can only ever be one of these types. This is a flag for
    the sole reason of facilitating unions in lookups using :func:`get_fields`.
    """

    INTERNAL = 1 << 0
    """Internal field that does not show up in the component's init signature."""
    CUSTOM_ID = 1 << 1
    """Field parsed into/from the component's custom id."""
    SELECT = 1 << 2
    """Field parsed from a select component's selected values."""
    MODAL = 1 << 3
    """Field parsed from a modal component's modal values."""

    ALL = (
        INTERNAL
        | CUSTOM_ID
        | SELECT
        | MODAL
    )
    """Meta-value for all field types.

    Mainly intended for use in :func:`get_fields`.
    """


def get_parser(field: "attrs.Attribute[typing.Any]") -> typing.Optional[parser_api.AnyParser]:
    """Get the user-provided parser of the provided field.

    Parameters
    ----------
    field:
        The field for which to get the :class:`ryoshu.api.Parser`.

    Returns
    -------
    :class:`ryoshu.api.Parser`
        The user-provided parser of the provided field.
    :data:`None`
        The field's parser was automatically inferred.

    """
    return field.metadata.get(FieldMetadata.PARSER)


def get_field_type(
    field: "attrs.Attribute[typing.Any]", default: _T = None,
) -> typing.Union[FieldType, _T]:
    """Get the :class:`FieldType` of the field.

    Parameters
    ----------
    field:
        The field of which to get the field type.
    default:
        The default value to use if the field doesn't have a :class:`FieldType`
        set.

    Returns
    -------
    :class:`FieldType`
        The type of the provided field.

    """
    return field.metadata.get(FieldMetadata.FIELDTYPE, default)


def is_field_of_type(field: "attrs.Attribute[typing.Any]", kind: FieldType) -> bool:
    """Check whether or not a field is marked as the provided :class:`FieldType`.

    Parameters
    ----------
    field:
        The field to check.
    kind:
        The :class:`FieldType` to check for.

    Returns
    -------
    :class:`bool`
        Whether the provided field was of the provided :class:`FieldType`.

    """
    set_type = field.metadata.get(FieldMetadata.FIELDTYPE)
    return bool(set_type and set_type & kind)  # Check if not None, then check if match.


def get_fields(cls: type, /, *, kind: FieldType = FieldType.ALL) -> typing.Sequence["attrs.Attribute[typing.Any]"]:
    r"""Get the Ryoshu fields of a class.

    Parameters
    ----------
    cls:
        The class of which to get the fields.
    kind:
        The kind(s) of fields to return. Can be any combination of
        :class:`FieldType`\s.

    """
    return [field for field in attrs.fields(cls) if is_field_of_type(field, kind)]


@typing.overload
def field(
    default: NothingType = NOTHING,
    *,
    factory: typing.Callable[[], _T],
    parser: typing.Optional[parser_api.ParserWithArgumentType[_T]] = None,
) -> _T:
    ...


@typing.overload
def field(
    default: _T,
    *,
    factory: None = None,
    parser: typing.Optional[parser_api.ParserWithArgumentType[_T]] = None,
) -> _T:
    ...


def field(
    default: typing.Union[_T, NothingType] = NOTHING,
    *,
    factory: typing.Optional[typing.Callable[[], _T]] = None,
    parser: typing.Optional[parser_api.ParserWithArgumentType[_T]] = None,
) -> _T:
    r"""Define a custom ID field for the component.

    The type annotation for this field is used to parse incoming custom ids.

    This is a wrapper around :func:`attrs.field`.

    Parameters
    ----------
    default:
        The default value for this field.
    parser:
        The parser to use for converting this field to and from a string.

    Returns
    -------
    :func:`Field <attrs.field>`\[``T``]
        A new field with the provided default and/or parser.

    """
    if factory is not None:
        if default is not NOTHING:
            message = "Please provide one of default or factory, not both."
            raise RuntimeError(message)

        default = attrs.Factory(factory)

    return attrs.field(
        default=typing.cast(_T, default),
        kw_only=True,
        metadata={
            FieldMetadata.FIELDTYPE: FieldType.CUSTOM_ID,
            FieldMetadata.PARSER: parser,
        },
    )


@typing.overload
def internal(
    default: NothingType = NOTHING,
    *,
    alias: typing.Optional[str] = None,
    factory: typing.Callable[[], _T],
    frozen: bool = False,
) -> _T:
    ...


@typing.overload
def internal(
    default: _T,
    *,
    alias: typing.Optional[str] = None,
    factory: None = None,
    frozen: bool = False,
) -> _T:
    ...



def internal(
    default: typing.Union[_T, NothingType] = NOTHING,
    *,
    alias: typing.Optional[str] = None,
    factory: typing.Optional[typing.Callable[[], _T]] = None,
    frozen: bool = False,
) -> _T:
    r"""Declare a field as internal.

    This is used internally to differentiate component parameters from
    user-defined custom id parameters.

    This is a wrapper around :func:`attrs.field`.

    Parameters
    ----------
    default:
        The default value for this field. The type of the default should match
        that of the type annotation.
    frozen:
        Whether or not the field should be marked frozen. A frozen field cannot
        be modified after the class has been created.

    Returns
    -------
    :func:`Field <attrs.field>`\[``T``]
        A new field with the provided default and frozen status.

    """
    if default is NOTHING:
        if factory is None:
            message = "Please provide either default or factory."
            raise RuntimeError(message)

        default = attrs.Factory(factory)

    elif factory is not None:
        message = "Please provide one of default or factory, not both."
        raise RuntimeError(message)

    return attrs.field(
        alias=alias,
        default=default,
        on_setattr=attrs.setters.frozen if frozen else None,
        metadata={FieldMetadata.FIELDTYPE: FieldType.INTERNAL},
    )
