import functools
import logging
import time

LOGGER = logging.getLogger('Lizmap')
DEBUG = True


def log_function(func):
    """ Decorator to log function. """
    @functools.wraps(func)
    def log_function_core(*args, **kwargs):
        LOGGER.info(f"Calling function {func.__name__}")
        value = func(*args, **kwargs)
        LOGGER.info(f"End of function {func.__name__} with return : {str(value)}")
        return value

    return log_function_core


def profiling(func):
    """ Decorator to make some profiling. """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        LOGGER.info("{} ran in {}s".format(func.__name__, round(end - start, 2)))
        return result

    return wrapper


def log_output_value(func):
    """ Decorator to log the output of the function. """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if DEBUG:
            LOGGER.info("{} output is {} for parameter {}".format(func.__name__, result, str(args)))
        else:
            LOGGER.info("{} output is {}… for parameter {}".format(func.__name__, result[0:200], str(args)))
        return result

    return wrapper
