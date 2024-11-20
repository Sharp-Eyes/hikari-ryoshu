hikari-ryoshu
=============

Ryoshu is a highly customisable, type-safe component manager for [hikari](https://github.com/hikari/hikari).
It is essentially a direct port of [disnake-ext-components](https://github.com/DisnakeCommunity/disnake-ext-components).
"Statelessness" is guaranteed by storing data in component custom ids and recovering the state from the custom id when the component is invoked.

Modal support is planned but currently not implemented.

Key Features
------------
- Smoothly integrates with hikari,
- Uses an intuitive dataclass-like syntax to create stateless persistent components,
- `custom_id` matching, conversion, and creation are automated for you,
- Highly customisable and expandable.

Installing
----------

**Python 3.9 or higher is required.** The exact hikari requirement is yet to be determined.
Since we only rely on listeners and component builders, I would assume it works with most even remotely recent versions of hikari.

To install the extension, run the following command in your command prompt/shell:

``` sh
# Linux/macOS
python3 -m pip install -U git+https://github.com/sharp-eyes/hikari-ryoshu

# Windows
py -3 -m pip install -U git+https://github.com/sharp-eyes/hikari-ryoshu
```
From there, it can be imported as:

```py
import ryoshu
```

Examples
--------
A very simple component that increments its label each time you click it can be written as follows:

```py
class MyButton(ryoshu.RichButton):
    count: int

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)

        self.count += 1
        self.label = str(self.count)

        await event.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            component=await ryoshu.into_action_row(self),
        )
```
A new component can then be instantiated as
```py
new_button = MyButton(label="0", count=0)
```
More complete examples can be found in [the examples folder](https://github.com/sharp-eyes/ryoshu/tree/main/examples).


Contributing
------------
Any contributions are welcome, feel free to open an issue or submit a pull request if you would like to see something added. Contribution guidelines will come soon.
