import logging
import os

from backup import settings
from backup.config.loader import load_config
from backup.config.logger import initialize_logger
from backup.config.models import Config
from backup.run import run_backup
from backup.utils import format_object


def main():
    # initialize logging configuration before doing anything
    # else so all log messages are captured.
    initialize_logger()

    logger = logging.getLogger(__name__)
    logger.info("backup application starting")
    logger.info("backup application settings: %s" % format_object(settings))

    config_path = settings.BACKUP_CONFIG_PATH
    config = load_config(path=config_path)

    if not config.enabled:
        logger.info("backup is disabled for configuration: '%s'", config.name)
        logger.info("backup will not be performed, exiting now")
    else:
        run_backup(
            config=config,
        )


# this is the main entry point for the application
# if the script is being run directly, we'll call the main function
# to start the application and run the backup process.

if __name__ == "__main__":
    main()
