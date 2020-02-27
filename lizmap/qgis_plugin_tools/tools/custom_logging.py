"""Setting up logging using QGIS, file, Sentry..."""

import logging

from qgis.core import QgsMessageLog, Qgis

from .i18n import tr
from .resources import plugin_name

PLUGIN_NAME = plugin_name()

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def qgis_level(logging_level):
    """Check for the corresponding QGIS Level according to Logging Level.

    For QGIS:
    https://qgis.org/api/classQgis.html#a60c079f4d8b7c479498be3d42ec96257

    For Logging:
    https://docs.python.org/3/library/logging.html#levels

    :param logging_level: The Logging level
    :type logging_level: basestring

    :return: The QGIS Level
    :rtype: Qgis.MessageLevel
    """
    if logging_level == 'CRITICAL':
        return Qgis.Critical
    elif logging_level == 'ERROR':
        return Qgis.Critical
    elif logging_level == 'WARNING':
        return Qgis.Warning
    elif logging_level == 'INFO':
        return Qgis.Info
    elif logging_level == 'DEBUG':
        return Qgis.Info

    return Qgis.Info


class QgsLogHandler(logging.Handler):
    """A logging handler that will log messages to the QGIS logging console."""

    def __init__(self, level=logging.NOTSET):
        logging.Handler.__init__(self)

    def emit(self, record):
        """Try to log the message to QGIS if available, otherwise do nothing.

        :param record: logging record containing whatever info needs to be
                logged.
        """
        try:
            QgsMessageLog.logMessage(
                record.getMessage(), PLUGIN_NAME, qgis_level(record.levelname))
        except MemoryError:
            message = tr(
                'Due to memory limitations on this machine, the plugin {} can not '
                'handle the full log').format(PLUGIN_NAME)
            print(message)
            QgsMessageLog.logMessage(message, PLUGIN_NAME, Qgis.Critical)


def add_logging_handler_once(logger, handler):
    """A helper to add a handler to a logger, ensuring there are no duplicates.

    :param logger: Logger that should have a handler added.
    :type logger: logging.logger

    :param handler: Handler instance to be added. It will not be added if an
        instance of that Handler subclass already exists.
    :type handler: logging.Handler

    :returns: True if the logging handler was added, otherwise False.
    :rtype: bool
    """
    class_name = handler.__class__.__name__
    for logger_handler in logger.handlers:
        if logger_handler.__class__.__name__ == class_name:
            return False

    logger.addHandler(handler)
    return True


def setup_logger(logger_name):
    """Run once when the module is loaded and enable logging.

    :param logger_name: The logger name that we want to set up.
    :type logger_name: basestring

    Borrowed heavily from this:
    http://docs.python.org/howto/logging-cookbook.html

    Now to log a message do::
       LOGGER.debug('Some debug message')
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # create formatter that will be added to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # create a QGIS handler
    qgis_handler = QgsLogHandler()

    # Set formatters
    console_handler.setFormatter(formatter)
    qgis_handler.setFormatter(formatter)

    # add the handlers to the logger
    add_logging_handler_once(logger, console_handler)
    add_logging_handler_once(logger, qgis_handler)
