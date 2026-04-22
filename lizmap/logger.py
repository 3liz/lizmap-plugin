import functools
import logging
import time

LOGGER = logging.getLogger('Lizmap')
DEBUG = True

# Re-export

debug = LOGGER.debug
info = LOGGER.info
warning = LOGGER.warning
error = LOGGER.error
critical = LOGGER.critical


def log_function(func):
    """ Decorator to log function. """
    @functools.wraps(func)
    def log_function_core(*args, **kwargs):
        LOGGER.info(f"Calling function {func.__name__}")
        value = func(*args, **kwargs)
        LOGGER.info(f"End of function {func.__name__} with return : {value!s}")
        return value

    return log_function_core


def profiling(func):
    """ Decorator to make some profiling. """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        LOGGER.info(f"{func.__name__} ran in {round(end - start, 2)}s")
        return result

    return wrapper


def log_output_value(func):
    """ Decorator to log the output of the function. """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if DEBUG:
            LOGGER.info(f"{func.__name__} output is {result} for parameter {args!s}")
        else:
            LOGGER.info(f"{func.__name__} output is {result[0:200]}… for parameter {args!s}")
        return result

    return wrapper
