import asyncio

import hikari
import ryoshu
import ryoshu.internal


async def main():
    i = hikari.Intents.ALL_DMS
    p = ryoshu.parser.get_parser(hikari.Intents)
    print(hikari.Intents.mro())
    print(type(p).__mro__)
    assert isinstance(p, ryoshu.parser.FlagParser)

    s = await ryoshu.internal.eval_maybe_coro(p.dumps(i))
    o = await ryoshu.internal.eval_maybe_coro(p.loads(s, source=None))
    print(s, i == o)


asyncio.run(main())