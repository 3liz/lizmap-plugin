import functools
import time

from qgis.core import Qgis, QgsMessageLog

PLUGIN = "Lizmap"
PROFILE = False


def info(message: str):
    QgsMessageLog.logMessage(message, PLUGIN, Qgis.MessageLevel.Info)


def warning(message: str):
    QgsMessageLog.logMessage(message, PLUGIN, Qgis.MessageLevel.Warning)


def critical(message: str):
    QgsMessageLog.logMessage(message, PLUGIN, Qgis.MessageLevel.Critical)


debug = info
error = critical


def log_function(func):
    """ Decorator to log function. """
    @functools.wraps(func)
    def log_function_core(*args, **kwargs):
        info(f"Calling function {func.__name__}")
        value = func(*args, **kwargs)
        info(f"End of function {func.__name__} with return : {value!s}")
        return value

    return log_function_core


def profiling(func):
    """ Decorator to make some profiling. """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        info(f"{func.__name__} ran in {round(end - start, 2)}s")
        return result

    return wrapper


def log_output_value(func):
    """ Decorator to log the output of the function. """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        debug(f"{func.__name__} output is {result} for parameter {args!s}")
        return result

    return wrapper
