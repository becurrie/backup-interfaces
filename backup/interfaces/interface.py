import importlib
import logging
import os
from abc import ABC, abstractmethod

from pydantic import BaseModel

from backup import settings
from backup.config.models import (
    BackupInterfaceConfig,
    StorageInterfaceConfig,
    VaultInterfaceConfig,
)
from backup.utils import format_object


class Interface(ABC):
    """Abstract base class for the `interface` pattern used throughout the application.

    This class provides a common interface for all interfaces in the application, an interface
    represents some sort of external service or resource that the application interacts with.

    The `Interface` class provides a common structure for all interfaces, including a configuration
    model and methods for validating that the configuration adheres to a model schema to prevent
    invalid configurations from being used.

    Attributes:
        config_cls: The configuration model class to use for the interface, this should be a
            pydantic BaseModel. This attribute should be set in concrete subclasses
            to define the configuration model that will be used for the interface.

    """

    config_cls = None

    def __init__(self, config):
        """Initialize the interface with a configuration.

        Args:
            config:

        Raises:
            ValidationError: If the configuration object does not adhere to the model
                schema defined by the `config_cls` attribute.

        """

        # we'll allow the config to be passed as a dictionary or as a pydantic model
        # for convenience, if it's a model, we'll convert it to a dictionary
        # before validating it below by instantiating a new model object with the
        # dictionary data.

        if isinstance(config, BaseModel):
            config = config.model_dump()

        # validate the configuration object using the model schema
        # for the interface, this will raise a validation error if
        # the configuration object does not adhere to the model schema.

        self.config = self.config_cls(**config)


class ClientInterfaceMixin(object):
    """Mixin class for interfaces that require a client object.

    This mixin class provides a common structure for interfaces that require
    a client object to interact with an external service. It provides a method
    for creating a client object using the configuration settings provided and will
    store the client object as an attribute of the interface for use in other methods.

    The `get_client` method should be implemented by subclasses to define the specific
    behavior of creating a client object for the interface.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = self.get_client()

    @abstractmethod
    def get_client(self):
        """Create a client object for the interface.

        This method should be implemented by subclasses to define the specific
        behavior of creating a client object for the interface. The implementation
        should handle the process of creating a client object for the configured
        service.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover


class BackupInterface(Interface):
    """Abstract base class for backup interfaces.

    This interface outlines the necessary methods and attributes that any
    concrete backup interface must implement. It provides a structure for
    creating backup mechanisms for various resources. Subclasses should
    implement the `backup` and `validate` methods to define their specific
    backup logic.

    """

    config_cls = BackupInterfaceConfig

    def __init__(self, config, storage):
        """Initialize the backup interface with a configuration and storage interface.

        Args:
            config: The configuration object for the backup interface.
            storage: The storage interface object to use for storing backups.

        """
        super().__init__(config)
        self.storage = storage

    @abstractmethod
    def validate(self):
        """Validate the backup configuration.

        This method should be called before the backup process is started
        to ensure that the configuration is valid and that the backup process
        can proceed.

        Note, this method should raise an exception if the configuration
        is not valid, and should provide a meaningful error message to
        help the user understand what is wrong with the configuration.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover

    @abstractmethod
    def archive(self, src):
        """Create an archive file of the specified resource.

        This method should be implemented by subclasses to define the specific
        behavior of creating an archive of the resource to be backed up. This is usually
        a temporary file that is created to store the backup data before it is uploaded
        to the storage interface.

        Args:
            src: The path to the resource to archive.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover

    @abstractmethod
    def backup(self):
        """Execute the backup process.

        This abstract method must be implemented by subclasses to define
        the specific behavior of the backup process. The implementation
        should handle the actual data backup mechanism for the configured resource.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover


class VaultInterface(Interface):
    """Abstract base class for vault interfaces.

    This interface outlines the necessary methods and attributes that any
    concrete vault interface must implement. It provides a structure for
    creating vault mechanisms for storing and retrieving secrets. Subclasses
    should implement the `get_secret` method to define their specific secret
    retrieval logic.

    Most vault will likely require the `ClientInterfaceMixin` to create a client
    object for interacting with the vault service, but this is not required, and we
    do not explicitly require it in the base interface.

    """

    config_cls = VaultInterfaceConfig

    @abstractmethod
    def get_secret(self, secret_name):
        """Retrieve a secret from the vault.

        This method should be implemented by subclasses to define the specific
        behavior of retrieving a secret from the vault. The implementation should
        handle the process of retrieving a secret from the configured vault service.

        Args:
            secret_name: The name of the secret to retrieve from the vault.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover


class StorageInterface(Interface):
    """Abstract base class for storage interfaces.

    This interface outlines the necessary methods and attributes that any
    concrete storage interface must implement. It provides a structure for
    creating storage mechanisms for storing and retrieving backups. Subclasses
    should implement the `store` and `retrieve` methods to define their specific
    storage logic.

    """

    config_cls = StorageInterfaceConfig

    def retention(self, path, config):
        """Apply retention policy to the storage service.

        This method should be implemented by subclasses to define the specific
        behavior of applying a retention policy to the storage service.

        By default, a very simple retention handler is implemented by default
        that will delete backups from the storage interface when the number of
        backups exceeds the configuration retention count.

        If a more complex retention policy is required, this method should be
        overridden in the subclass to implement the desired behavior, such as
        deleting backups based on age, size, or other criteria.

        Args:
            path: The path to the directory to apply the retention policy to.
            config: The retention policy configuration to apply.

        """
        logger = logging.getLogger(__name__)
        logger.info("applying retention policy to storage service: '%s'", path)
        logger.debug("retention policy configuration: %s", format_object(config))

        for i, item in enumerate(self.list(path=path)):
            if i >= config.count:
                self.delete(item)

    @abstractmethod
    def create(self, path):
        """Create a directory in the storage service.

        This method should be implemented by subclasses to define the specific
        behavior of creating a directory in the storage service.

        Args:
            path: The path to the directory to create.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover

    @abstractmethod
    def exists(self, path):
        """Check if a file exists in the storage service.

        This method should be implemented by subclasses to define the specific
        behavior of checking if a file exists in the storage service.

        Args:
            path: The path to the file to check.

        """
        pass  # pragma: no cover

    @abstractmethod
    def upload_chunk(self, *args, **kwargs):
        """Upload a chunk of a file to the storage service.

        This method should be implemented by subclasses to define the specific
        behavior of uploading a chunk of a file to the storage service.

        The arguments and keyword arguments for this method will vary depending
        on the specific storage service being used.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover

    @abstractmethod
    def upload(self, file, file_size, dst):
        """Upload a file to the storage service.

        This method should be implemented by subclasses to define the specific
        behavior of uploading a file in to the storage service.

        Args:
            file: The file to upload.
            file_size: The size of the file to upload.
            dst: The name of the file to store.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover

    @abstractmethod
    def delete(self, path):
        """Delete a backup from the storage service.

        This method should be implemented by subclasses to define the specific
        behavior of deleting a file from the storage service.

        Args:
            path: The name of the file to delete.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover

    @abstractmethod
    def list(self, path):
        """List all files in the storage service at the specified path.

        This method should be implemented by subclasses to define the specific
        behavior of listing fies stored in the storage service.

        Args:
            path: The path to list files from.

        Raises:
            NotImplementedError: If this method is called without
                being overridden in a subclass.

        """
        pass  # pragma: no cover
