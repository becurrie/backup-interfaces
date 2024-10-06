import logging
import time
from functools import wraps


def log_execution(name=__name__, level=logging.DEBUG, prefix=None):
    """Global decorator to log function execution time.

    This decorator logs the execution time of a function in milliseconds and displays a message
    indicating the time taken to execute the function. The log message is written to the root
    logger with the specified log level and includes the function name, execution time, and an
    optional prefix message.

    Args:
        name (str): The name of the logger to use when logging the execution time.
        level (int): The log level to use when logging the execution time.
        prefix (str): An optional message to include in the log message.

    Returns:
        function: The decorated function.

    Examples:
        >>> @log_execution(level=logging.DEBUG, prefix="executed function")
        ... def my_function():
        ...     pass
        ...
        >>> my_function()
        DEBUG:root:Ran function: 0.0001 ms

    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(name)

            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            execution_time = (end_time - start_time) * 1000
            message_prefix = "%s: " % prefix if prefix else ""
            message = "%s%.4f seconds" % (message_prefix, execution_time)

            logger.log(
                level=level,
                msg=message,
            )

            return result

        return wrapper

    return decorator
