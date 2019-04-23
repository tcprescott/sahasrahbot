import inspect
import logging


def debug(info_str: str):
    caller_mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    logging.getLogger('alttpr-discord-bot').debug('[{0}] {1}'.format(caller_mod_name, info_str))


def info(info_str: str):
    caller_mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    logging.getLogger('alttpr-discord-bot').info('[{0}] {1}'.format(caller_mod_name, info_str))


def warning(error_str: str):
    caller_mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    logging.getLogger('alttpr-discord-bot').warning('[{0}] {1}'.format(caller_mod_name, error_str))


def error(error_str: str):
    caller_mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    logging.getLogger('alttpr-discord-bot').error('[{0}] {1}'.format(caller_mod_name, error_str), exc_info=True)


def critical(error_str: str):
    caller_mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    logging.getLogger('alttpr-discord-bot').critical('[{0}] {1}'.format(caller_mod_name, error_str), exc_info=True)