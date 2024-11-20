"""Implementation of component base classes.

To easily integrate with Ryoshu, it is recommended to inherit
from any of these base classes. In any case, it is very much recommended to at
least use the `ComponentMeta` metaclass. Without this, a lot of internal
functionality will have to be manually re-implemented.
"""

from __future__ import annotations

import abc
import inspect
import sys
import typing

import attrs
import typing_extensions
from ryoshu import fields as fields
from ryoshu.api import component as component_api
from ryoshu.impl import factory as factory_impl
from ryoshu.impl import parser as parser_impl

__all__: typing.Sequence[str] = ("ComponentBase",)


def _is_attrs_pass(namespace: typing.Dict[str, typing.Any]) -> bool:
    """Check if attrs has already influenced the class' namespace.

    Note that we check the namespace instead of using `attrs.has`, because
    `attrs.has` would always return `True` for a class inheriting an attrs class,
    and we specifically need to distinguish between the two passes inside
    `ComponentMeta.__new__`.
    """
    return namespace.get("__attrs_attrs__") is not None


def _eval_type(cls: type, annotation: typing.Any) -> typing.Any:  # noqa: ANN401
    # Get the module globals in which the class was defined. This is the most
    # probable candidate in which to find the type annotations' definitions.
    #
    # For the most part, this should be safe. Conflicts where e.g. a component
    # inheriting from RichButton but not defining _AnyEmoji in their own module
    # are safe, because the type has already been passed through this function
    # when the RichButton class was initially created.
    cls_globals = sys.modules[cls.__module__].__dict__

    if isinstance(annotation, str):
        annotation = typing.ForwardRef(annotation, is_argument=False)

    # Evaluate the typehint with the provided globals.
    return typing._eval_type(annotation, cls_globals, None)  # pyright: ignore


def _validate_overwrite(
    attribute: attrs.Attribute[object],
    super_field_type: fields.FieldType,
    overwrite_field_type: typing.Optional[fields.FieldType],
) -> None:
    if overwrite_field_type is None or overwrite_field_type is super_field_type:
        return

    message = (
        f"Invalid field override: field {attribute.name} is defined as a(n)"
        f" {super_field_type.name} field, but was overwritten as a(n)"
        f" {overwrite_field_type.name} field."
    )
    raise TypeError(message)


def _field_transformer(cls: type, attributes: list[attrs.Attribute[object]]) -> list[attrs.Attribute[object]]:
    # Collect attrs from superclasses...
    super_fields = fields.get_fields(cls) if attrs.has(cls) else ()
    super_attributes = {field.name: field for field in super_fields}

    finalised_attributes: list[attrs.Attribute[object]] = []
    for attribute in attributes:
        field_type = fields.get_field_type(attribute)
        attribute_type = _eval_type(cls, attribute.type)
        metadata = attribute.metadata.copy()

        # Overwrite of an existing field...
        if attribute.name in super_attributes:
            super_attribute = super_attributes[attribute.name]

            # Ensure field type hasn't changed...
            super_field_type = fields.get_field_type(super_attribute)
            assert super_field_type is not None  # Guaranteed to exist.
            _validate_overwrite(attribute, super_field_type, field_type)

            # "Inherit" metadata where needed...
            for metadata_key in fields.FieldMetadata:
                if metadata.get(metadata_key) is None:
                    metadata[metadata_key] = super_attribute.metadata[metadata_key]

        # New field without explicit field type: default to custom id field...
        elif metadata.get(fields.FieldMetadata.FIELDTYPE) is None:
            metadata[fields.FieldMetadata.FIELDTYPE] = fields.FieldType.CUSTOM_ID

        # Set a parser if there isn't one already...
        if metadata.get(fields.FieldMetadata.PARSER) is None:
            metadata[fields.FieldMetadata.PARSER] = (
                parser_impl.get_parser(attribute_type)
                if field_type is fields.FieldType.CUSTOM_ID
                else None
            )

        # Apply finalised metadata...
        finalised_attributes.append(attribute.evolve(type=attribute_type, metadata=metadata))

    return finalised_attributes


@typing_extensions.dataclass_transform(
    kw_only_default=True, field_specifiers=(fields.field, fields.internal)
)
class ComponentMeta(abc.ABCMeta):
    """Metaclass for all Ryoshu component types.

    It is **highly** recommended to use this metaclass for any class that
    should interface with the components api exposed by Ryoshu.

    This metaclass handles :mod:`attrs` class generation, custom id completion,
    interfacing with component managers, parser and factory generation, and
    automatic slotting.
    """

    # HACK: Pyright doesn't like this but it does seem to work with typechecking
    #       down the line. I might change this later (e.g. define it on
    #       BaseComponent instead, but that comes with its own challenges).
    factory: component_api.ComponentFactory[typing_extensions.Self]  # pyright: ignore

    def __new__(
        mcls,  # pyright: ignore[reportSelfClsParameterName]
        name: str,
        bases: tuple[type, ...],
        namespace: typing.Dict[str, typing.Any],
    ) -> ComponentMeta:
        # NOTE: This is run twice for each new class; once for the actual class
        #       definition, and once more by attrs.define(). We ensure we only
        #       run the full class creation logic once.

        # Set slots if attrs hasn't already done so...
        namespace.setdefault("__slots__", ())

        cls = typing.cast("type[ComponentBase]", super().__new__(mcls, name, bases, namespace))
        if _is_attrs_pass(namespace):
            return cls

        cls = attrs.define(cls, slots=True, kw_only=True, field_transformer=_field_transformer)

        factory_cls = factory_impl.NoopFactory if inspect.isabstract(cls) else factory_impl.ComponentFactory
        cls.factory = factory_cls.from_component(cls)
        return cls


class ComponentBase(component_api.ManagedComponent, metaclass=ComponentMeta):
    """Overarching base class for any kind of component."""

    manager: typing.ClassVar[typing.Optional[component_api.ComponentManager]] = None
    """The manager to which this component is registered.

    Defaults to :obj:`None` if this component is not registered to any manager.
    """

    factory = factory_impl.NoopFactory()
    r"""Factory type that builds instances of this class.

    Since component base classes can be declared as :class:`~typing.Protocol`\s
    and protocols cannot be instantiated, this attribute defaults to a
    :class:`~NoopFactory`. In case a concrete component subclass is created, a matching
    :class:`~ComponentFactory` is automatically generated instead.
    """

    async def make_custom_id(self) -> str:
        """Make a custom id from this component given its current state.

        The generated custom id will contain the full state of the component,
        such that it be used to entirely reconstruct the component later.

        .. note::
            As the logic for translating a component to and from a custom id
            resides inside the component manager, the component *must* be
            registered to a manager to use this method.

        Returns
        -------
        str:
            The custom id representing the full state of this component.

        """
        if not self.manager:
            message = (
                "A component must be registered to a manager to create a custom"
                "id. Please register this component to a manager before trying"
                "to create a custom id for it."
            )
            raise RuntimeError(message)

        return await self.manager.make_custom_id(self)
