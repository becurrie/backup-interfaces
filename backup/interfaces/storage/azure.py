import logging
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient
from pydantic import BaseModel
from tqdm import tqdm

from backup import settings
from backup.config.models import StorageInterfaceConfig
from backup.decorators import log_execution
from backup.interfaces.interface import ClientInterfaceMixin, StorageInterface

file_lock = threading.Lock()


class AzureBlobStorageInterfaceConfig(StorageInterfaceConfig):
    storage_account: str
    storage_container: str
    storage_key: str


class AzureBlobStorageInterface(ClientInterfaceMixin, StorageInterface):
    """Concrete implementation of a storage interface for storing backups in Azure Blob Storage.

    This class provides methods for storing backups in Azure Blob Storage. It connects to the
    Azure Blob Storage service and manages the process of storing and retrieving backups using
    the specified configuration settings.

    The only required setup required outside your interface configuration is to create a
    storage container within the configured blob storage account. This can be done using the
    Azure Portal or the Azure CLI.

    Any backups stored using this interface during runtime will be stored in the specified
    container within the configured Azure Blob Storage account.

    Settings:

    - storage_account (str): The name of the Azure Blob Storage account.
        This is the name of the Azure Blob Storage account that the interface will connect to,
        and where backups will be stored.

    - storage_container (str): The name of the Azure Blob Storage container.
        This is the name of the Azure Blob Storage container that the interface will use to store
        backups. The container must exist within the specified Azure Blob Storage account prior
        to using the interface.

    - storage_key (str): The access key for the Azure Blob Storage account.
        This is the access key for the Azure Blob Storage account that the interface will use
        to authenticate with the Azure Blob Storage service.

    """

    config_cls = AzureBlobStorageInterfaceConfig
    account_url_template = "https://%s.blob.core.windows.net"

    def get_client(self):
        """Create a client object for the azure blob storage service.

        Returns:
            azure.storage.blob.BlobServiceClient: A client object for the azure blob storage service.

        Raises:
            Exception: If the client object cannot be created due to invalid
                configuration settings or connectivity issues.

        """
        return BlobServiceClient(
            account_url=self.account_url_template % self.config.storage_account,
            credential=self.config.storage_key,
        ).get_container_client(
            container=self.config.storage_container,
        )

    @log_execution(
        __name__,
        prefix="created directory in azure blob storage",
    )
    def create_directory(self, path):
        """Create a directory in the azure blob storage container.

        Args:
            path (str): The path of the directory to create.

        Raises:
            ResourceExistsError: If the directory already exists.

        """
        logger = logging.getLogger(__name__)
        logger.info("creating directory in azure blob storage: '%s'", path)

        blob = self.client.get_blob_client(path)
        blob.upload_blob(b"", overwrite=False)

    def exists(self, path):
        """Check if a file or directory exists in the azure blob storage container.

        Args:
            path (str): The path of the directory to check.

        Returns:
            bool: True if the file exists, False otherwise.

        """
        logger = logging.getLogger(__name__)
        logger.debug("checking if blob exists in azure blob storage: '%s'", path)

        try:
            # as long as we can the blob properties, the file exists
            # within azure blob storage.
            blob = self.client.get_blob_client(path)
            blob.get_blob_properties()
        except ResourceNotFoundError:
            return False

        return True

    def upload_chunk(
        self, blob_client, file, offset, length, chunk_id, chunk_size, progress
    ):
        """Upload a chunk of a file to the azure blob storage container.

        This method is meant to be used in conjunction with the `upload` method to
        upload a file to the azure blob storage container in chunks.

        We use a separate method for uploading chunks so that we can use a ThreadPoolExecutor
        to upload multiple chunks concurrently.

        Args:

            blob_client (azure.storage.blob.BlobClient): The blob client object for the
                file to upload.
            file: The file to upload.
            offset (int): The offset in the file to start reading from.
            length (int): The length of the chunk to read.
            chunk_id (str): The id of the chunk to upload.
            chunk_size (int): The size of the chunk to upload.
            progress (tqdm): A tqdm progress bar to update with the progress of the upload.

        """

        # use the `file_lock` here to ensure threads don't concurrently
        # access the file handle and cause issues with reading the file.

        with file_lock:
            file.seek(offset)
            file_data = file.read(length)

        # stage our block in the azure blob storage container, and update the
        # progress bar if it is provided.

        blob_client.stage_block(
            block_id=chunk_id,
            data=file_data,
        )
        if progress:
            progress.update(len(file_data))

    @log_execution(
        __name__,
        prefix="uploaded file to azure blob storage",
    )
    def upload(self, file, file_size, dst, progress=None):
        """Upload a file or directory to an azure blob storage container in
        chunks of size `settings.BACKUP_UPLOAD_CHUNK_SIZE`.

        Note that by default, the file being uploaded will be uploaded in chunks
        to the storage interface with the specified path. The file will be uploaded
        concurrently with a maximum of `settings.BACKUP_UPLOAD_CONCURRENCY` threads
        uploading chunks of the file to the storage interface before committing the
        file to the storage interface.

        Args:
            file (file): The file to upload.
            file_size (int): The size of the file to upload.
            dst (str): The path to upload the file to.
            progress (dict): A dictionary of keyword arguments to pass to the tqdm
                progress bar.

        """
        logger = logging.getLogger(__name__)
        logger.info("uploading file to azure blob storage: '%s'", dst)

        blob_client = self.client.get_blob_client(dst)
        blob_chunk_size = settings.BACKUP_UPLOAD_CHUNK_SIZE
        blob_chunk_workers = settings.BACKUP_UPLOAD_CONCURRENCY
        blob_chunk_ids = []
        blob_chunk_index = 0

        if progress:
            progress = tqdm(**progress)

        with ThreadPoolExecutor(max_workers=blob_chunk_workers) as executor:
            for blob_chunk_offset in range(0, file_size, blob_chunk_size):
                blob_chunk_length = min(blob_chunk_size, file_size - blob_chunk_offset)
                blob_chunk_id = str(blob_chunk_offset).zfill(16)
                blob_chunk_ids.append(blob_chunk_id)
                executor.submit(
                    self.upload_chunk,
                    blob_client,
                    file,
                    blob_chunk_offset,
                    blob_chunk_length,
                    blob_chunk_id,
                    blob_chunk_size,
                    progress,
                )
        blob_client.commit_block_list(blob_chunk_ids)

    @log_execution(
        __name__,
        prefix="deleted file from azure blob storage",
    )
    def delete(self, path):
        """Delete a file from the azure blob storage container.

        Args:
            path (str): The path of the file to delete.

        """
        logger = logging.getLogger(__name__)
        logger.info("deleting file from azure blob storage: '%s'", path)

        blob = self.client.get_blob_client(path)
        blob.delete_blob()

    def list(self, path):
        """List all sorted files in the azure blob storage container at
        the specified path.

        The files are sorted so that the most recent files are listed first, note that
        some additional processing is done to ensure the file path specified is parsed
        correctly to support azure blob storage requirements.

        Args:
            path (str): The path to list files from.

        Returns:
            List[str]: A list of file names within the specified path.

        """
        logger = logging.getLogger(__name__)
        logger.debug("listing files in azure blob storage: '%s'", path)

        path = path.replace("\\", "/")

        return sorted(
            [
                blob.name
                for blob in self.client.list_blobs(name_starts_with=path)
                if blob.name != path
            ],
            key=lambda f: os.path.splitext(f)[0].lower(),
            reverse=True,
        )
