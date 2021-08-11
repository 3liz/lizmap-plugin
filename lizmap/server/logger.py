__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import functools
import traceback

from contextlib import contextmanager

from qgis.core import Qgis, QgsMessageLog

PLUGIN = 'Lizmap'


class Logger:

    @staticmethod
    def info(message):
        QgsMessageLog.logMessage(PLUGIN + ' : ' + message, PLUGIN, Qgis.Info)

    @staticmethod
    def warning(message):
        QgsMessageLog.logMessage(PLUGIN + ' : ' + message, PLUGIN, Qgis.Warning)

    @staticmethod
    def critical(message):
        QgsMessageLog.logMessage(PLUGIN + ' : ' + message, PLUGIN, Qgis.Critical)

    @staticmethod
    def log_exception(e):
        """ Log a Python exception. """
        QgsMessageLog.logMessage(
            "Exception: {plugin}\n{e}\n{traceback}".format(
                plugin=PLUGIN,
                e=e,
                traceback=traceback.format_exc()
            ),
            PLUGIN,
            Qgis.Critical
        )


def exception_handler(func):
    """ Decorator to catch all exceptions. """
    def inner_function(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            Logger.log_exception(e)
    return inner_function


@contextmanager
def trap():
    """ Define a trap context for catching all exceptions """
    try:
        yield
    except Exception as e:
        Logger.log_exception(e)


def log_function(func):
    """ Decorator to log function. """
    @functools.wraps(func)
    def log_function_core(*args, **kwargs):
        QgsMessageLog.logMessage('{}.{}'.format(PLUGIN, func.__name__), PLUGIN, Qgis.Info)
        value = func(*args, **kwargs)
        return value

    return log_function_core
