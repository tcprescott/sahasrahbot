import argparse
import sys
import shlex

def parse_args(message):
    split_msg = ['sb'] + shlex.split(message)

    parser = SrlArgumentParser()
    parser.add_argument('base', type=str)

    subparsers = parser.add_subparsers(dest="command")

    parser_preset = subparsers.add_parser('$preset')
    parser_preset.add_argument('preset')
    parser_preset.add_argument('--hints', action='store_true')
    parser_preset.add_argument('--silent', action='store_true')

    parser_custom = subparsers.add_parser('$custom')

    parser_spoiler = subparsers.add_parser('$spoiler')
    parser_spoiler.add_argument('preset')
    parser_spoiler.add_argument('--studytime', type=int)
    parser_spoiler.add_argument('--silent', action='store_true')

    parser_random = subparsers.add_parser('$random')
    parser_random.add_argument('weightset', nargs='?', default="weighted")
    parser_random.add_argument('--silent', action='store_true')

    parser_mystery = subparsers.add_parser('$mystery')
    parser_mystery.add_argument('weightset', nargs='?', default="weighted")
    parser_mystery.add_argument('--silent', action='store_true')

    parser_join = subparsers.add_parser('$joinroom')
    parser_join.add_argument('channel')

    parser_leave = subparsers.add_parser('$leave')

    parser_cancel = subparsers.add_parser('$cancel')

    parser_vt = subparsers.add_parser('$vt')

    parser_echo = subparsers.add_parser('$echo')
    parser_echo.add_argument('message')

    parser_help = subparsers.add_parser('$help')

    
    args = parser.parse_args(split_msg)

    return args

class SrlArgumentParser(argparse.ArgumentParser):    
    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        If only it were made available in the ArgumentError object. It is 
        passed as it's first arg...
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if '/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        exc = sys.exc_info()[1]
        if exc:
            exc.argument = self._get_action_from_name(exc.argument_name)
            raise exc
        # super(SrlArgumentParser, self).error(message)