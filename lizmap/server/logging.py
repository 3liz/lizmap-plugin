__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import functools

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


def log_function(func):
    """ Decorator to log function. """
    @functools.wraps(func)
    def log_function_core(*args, **kwargs):
        QgsMessageLog.logMessage('{}.{}'.format(PLUGIN, func.__name__), PLUGIN, Qgis.Info)
        value = func(*args, **kwargs)
        return value

    return log_function_core
