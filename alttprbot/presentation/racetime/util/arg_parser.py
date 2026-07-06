"""Command-line style argument parsing for RaceTime ``ex2_*`` chat commands.

Ported from the previously-used racetime-bot fork's ``racetime_bot.utils.arg_parser``.
The official upstream package (2.3.0) dropped its ``utils`` module and only dispatches
``ex_*`` commands, so this parser lives here to keep the ``ex2_*`` command contract
(mixed positional/keyword parsing, e.g. ``!newrace --preset=standard --branch=live``)
that SahasrahBot handlers rely on.
"""


def arg_parser(s):
    """
    Parse a string into positional and keyword arguments.

    Positional arguments are separated by spaces.
    Keyword arguments are separated by spaces and start with --.
    Keyword arguments can be specified as --key=value or --key value.
    Keyword arguments without a value are treated as boolean flags.
    Boolean flags can be negated by prepending no- to the key.

    Returns a tuple of (positionals, keywords).
    """
    a = s.split()
    positionals = []
    keywords = {}
    for arg in a:
        if arg.startswith("--"):
            try:
                key, val = arg[2:].split("=")

                # attempt to convert to int
                try:
                    val = int(val)
                except ValueError:
                    pass

                # convert to bool if possible
                if val == 'true':
                    val = True
                elif val == 'false':
                    val = False

            except ValueError:
                key = arg[2:]
                if key.startswith("no-"):
                    key = key[3:]
                    val = False
                else:
                    val = True
            keywords[key] = val
        elif arg.startswith("-"):
            key = arg[1:]
            keywords[key] = True
        else:
            positionals.append(arg)

    return positionals, keywords
