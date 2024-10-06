import logging

from backup import settings
from backup.utils import get_class


def run_backup(config):
    """Run the backup process using the provided configuration.

    Args:
        config: The configuration object to use for the backup process.

    """
    logger = logging.getLogger(__name__)
    logger.info("starting backup process")
    logger.info("using backup configuration: '%s'", config.name)

    # initialize storage interface as specified in the configuration.
    # this will be used to store the backups created by the backup interfaces.

    storage_config = config.storage
    storage_class = get_class(cls=storage_config.interface)
    storage_instance = storage_class(config=storage_config)

    # initialize backup interfaces as specified in the configuration.
    # these will be used to create the backups that will be stored by the storage interface.

    interface_configs = []
    interface_instances = []

    for interface in config.interfaces:
        interface_configs.append(interface)
    for interface in interface_configs:
        if not interface.enabled:
            logger.info(
                "backup interface: '%s' is disabled, interface will be skipped",
                interface.interface,
            )
        else:
            interface_class = get_class(cls=interface.interface)
            interface_instance = interface_class(
                config=interface,
                storage=storage_instance,
            )
            interface_instances.append(interface_instance)

    for interface in interface_instances:
        interface.validate()
        interface.backup()
