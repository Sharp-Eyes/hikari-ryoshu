"""Standard implementation of the overarching component factory type."""

import types
import typing

import attr
import typing_extensions

from ryoshu import fields
from ryoshu.api import component as component_api
from ryoshu.api import parser as parser_api
from ryoshu.impl.parser import base as parser_base
from ryoshu.internal import aio

__all__: typing.Sequence[str] = ("ComponentFactory",)


ParserMapping = typing.Mapping[str, parser_base.AnyParser]


@attr.define(slots=True)
class ComponentFactory(
    component_api.ComponentFactory[component_api.ComponentT],
    typing.Generic[component_api.ComponentT],
):
    """Implementation of the overarching component factory type.

    A component factory holds information about all the custom id fields of a
    component, and contains that component's parsers. In most situations, a
    component factory can simply be created using :meth:`from_component`.
    """

    parsers: ParserMapping = attr.field(converter=types.MappingProxyType)  # pyright: ignore[reportGeneralTypeIssues]
    """A mapping of custom id field name to that field's parser."""
    component: type[component_api.ComponentT]
    """The component type that this factory builds."""

    @classmethod
    def from_component(cls, component: type[component_api.ManagedComponent]) -> typing_extensions.Self:
        # <<docstring inherited from api.components.ComponentFactory>>
        parser: typing.Optional[parser_api.AnyParser]

        parsers: dict[str, parser_base.AnyParser] = {}
        for field in fields.get_fields(component, kind=fields.FieldType.CUSTOM_ID):
            parser = fields.get_parser(field)

            if not parser:
                field_type = field.type or str
                parser = parser_base.get_parser(field_type).default(field_type)

            assert isinstance(parser, parser_base.Parser)
            parsers[field.name] = parser

        return cls(
            parsers,
            typing.cast(type[component_api.ComponentT], component),
        )

    async def loads_param(self, param: str, value: str) -> object:
        """Parse a single custom id parameter to the desired type with its parser.

        Parameters
        ----------
        param:
            The name of the custom id field that is to be parsed.
        value:
            The value of the custom id field that is to be parsed.
        source:
            The source object used to parse the custom id parameter.

        Returns
        -------
        :class:`object`:
            The parsed custom id field value.

        """
        parser = self.parsers[param]
        return await aio.eval_maybe_coro(parser.loads(value))

    async def dumps_param(self, param: str, value: object) -> str:
        """Parse a single custom id parameter to its string form for custom id storage.

        Parameters
        ----------
        param:
            The name of the custom id field that is to be parsed.
        value:
            The value of the custom id field that is to be parsed.

        Returns
        -------
        :class:`str`:
            The dumped custom id parameter, ready for storage inside a custom id.

        """
        parser = self.parsers[param]
        result = parser.dumps(value)
        return await aio.eval_maybe_coro(result)

    async def load_params(self, params: typing.Sequence[str], /) -> typing.Mapping[str, object]:
        # <<docstring inherited from api.components.ComponentFactory>>

        if len(params) != len(self.parsers):
            # Ensure params and parsers are of the same length before zipping them.
            # Equivalent to `zip(..., strict=True)` in py >= 3.10.
            message = (
                "Component parameter count mismatch."
                f" Expected {len(self.parsers)}, got {len(params)}."
            )
            raise ValueError(message)

        return {
            param: await self.loads_param(param, value)
            for param, value in zip(self.parsers, params)
            if value
        }

    async def dump_params(self, component: component_api.ComponentT, /) -> typing.Mapping[str, str]:
        # <<docstring inherited from api.components.ComponentFactory>>

        return {
            field: await self.dumps_param(field, getattr(component, field))
            for field in self.parsers
        }

    async def build_component(
        self,
        params: typing.Sequence[str],
        component_params: typing.Optional[typing.Mapping[str, object]] = None,
    ) -> component_api.ComponentT:
        # <<docstring inherited from api.components.ComponentFactory>>

        parsed = await self.load_params(params)
        return self.component(**parsed, **(component_params or {}))


class NoopFactory(component_api.ComponentFactory[typing.Any]):
    """Factory class to make component protocols typesafe.

    Since component protocols cannot be instantiated, building a factory with
    parsers for them does not make sense. Instead, they will receive one of
    these to remain typesafe. Any operation on a NoopFactory will raise
    :class:`NotImplementedError`.
    """

    __slots__: typing.Sequence[str] = ()
    __instance: typing.ClassVar[typing.Optional[typing_extensions.Self]] = None

    def __new__(cls) -> typing_extensions.Self:
        if cls.__instance is not None:
            return cls.__instance

        cls.__instance = self = super().__new__(cls)
        return self

    @classmethod
    def from_component(
        cls, _: type[component_api.ManagedComponent],
    ) -> typing_extensions.Self:
        # <<docstring inherited from api.components.ComponentFactory>>

        return cls()

    async def load_params(self, component: object, /) -> typing.NoReturn:
        # <<docstring inherited from api.components.ComponentFactory>>

        raise NotImplementedError

    async def dump_params(self, component: object, /) -> typing.NoReturn:
        # <<docstring inherited from api.components.ComponentFactory>>

        raise NotImplementedError

    async def build_component(
        self,
        params: typing.Sequence[str],
        component_params: typing.Optional[typing.Mapping[str, object]] = None,
    ) -> typing.NoReturn:
        # <<docstring inherited from api.components.ComponentFactory>>

        raise NotImplementedError

    def __repr__(self) -> str:
        return "<NoopFactory>"
