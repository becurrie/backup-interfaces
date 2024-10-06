import json
import logging
import logging.config
import os
import pprint
import types
from logging.handlers import HTTPHandler, RotatingFileHandler

from backup import settings


def initialize_logger():
    """Initialize the logging configuration for the application.

    This function sets up the logging configuration for the application,
    including the creation of loggers, handlers, and formatters. It
    configures logging to output messages to both the console and a
    rotating log file. The logging level, file directory, file name,
    and formatting are determined by the application's settings.

    Additionally, this function ensures that the log directory exists
    by creating it if it does not already exist on the filesystem.
    This is important to prevent errors when the application attempts
    to write logs to the specified file.

    Raises:
        OSError: If the log directory cannot be created or accessed.

    This function should typically be called once during application
    startup to configure logging before any log messages are generated.

    """
    if not os.path.exists(settings.LOG_FILE_DIR):
        os.makedirs(settings.LOG_FILE_DIR)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": settings.LOG_FORMAT,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": os.path.join(
                        settings.LOG_FILE_DIR, settings.LOG_FILE_NAME
                    ),
                    "maxBytes": settings.LOG_FILE_MAX_SIZE,
                    "backupCount": settings.LOG_FILE_RETENTION,
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console", "file"],
                    "level": settings.LOG_LEVEL,
                },
            },
        }
    )

    # set logging from external libraries to a higher level to avoid
    # excessive logging output in the application logs, especially
    # when running in production environments. We still want error logs
    # for most external libraries, but we don't need to see all the
    # debug and info messages.

    logging.getLogger("azure").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("pydantic").setLevel(logging.ERROR)
    logging.getLogger("paramiko").setLevel(logging.ERROR)
