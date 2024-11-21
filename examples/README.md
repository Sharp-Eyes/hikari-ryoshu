Examples
========

This folder contains examples for the Ryoshu library.

Note: The examples use raw hikari to register commands.
This is done so that the examples can be run as reproducible standalone scripts.
Ryoshu itself is independent of any command manager, so command registration can be done with a command manager of your choice.

Examples can be easily run by cloning the repository and invoking the `example` script with the filename of the example you wish to run:
```shell
git clone https://github.com/sharp-eyes/hikari-ryoshu

uv run example button
```