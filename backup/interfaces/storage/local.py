import logging
import os
import shutil
import tarfile
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List

from pydantic import BaseModel
from tqdm import tqdm

from backup import settings
from backup.config.models import StorageInterfaceConfig
from backup.decorators import log_execution
from backup.interfaces.interface import StorageInterface

file_lock = threading.Lock()


class LocalStorageInterface(StorageInterface):
    """Concrete implementation of a storage interface for storing backups on the local filesystem.

    This class provides methods for storing backups on the local filesystem. It manages the process
    of storing and retrieving backups using the specified configuration settings.

    No additional setup is required to get local storage working. Any backups stored using this
    interface during runtime will be stored on the local filesystem at the specified path.

    """

    config_cls = StorageInterfaceConfig

    @log_execution(
        __name__,
        prefix="created directory in local filesystem",
    )
    def create_directory(self, path):
        """Create a directory on the local filesystem.

        Args:
            path (str): The path to the directory to create.

        """
        logger = logging.getLogger(__name__)
        logger.info("creating directory in local filesystem: '%s'", path)

        os.makedirs(
            path,
            exist_ok=True,
        )

    def exists(self, path):
        """Check if a file or directory exists on the local filesystem.

        Args:
            path (str): The path to the file to check.

        Returns:
            bool: True if the file exists, False otherwise.

        """
        logger = logging.getLogger(__name__)
        logger.debug("checking if file exists in local filesystem: '%s'", path)

        return os.path.exists(
            path,
        )

    def upload_chunk(self, file, file_dst, offset, length, chunk_size, progress):
        """Upload a chunk of a file to the local filesystem.

        This method reads a chunk of the file and writes it to the destination file.

        We use a separate method for uploading chunks so that we can use a ThreadPoolExecutor
        to upload multiple chunks concurrently.

        Args:
            file (file): The file to upload.
            file_dst (file): The file to upload to.
            offset (int): The offset in the file to start reading from.
            length (int): The length of the chunk to read.
            chunk_size (int): The size of the chunk to upload.
            progress (tqdm): A tqdm progress bar to update with the progress of the upload.

        """
        with file_lock:
            file.seek(offset)
            file_data = file.read(length)

        with file_lock:
            file_dst.seek(offset)
            file_dst.write(file_data)

        if progress:
            progress.update(len(file_data))

    @log_execution(
        __name__,
        prefix="uploaded file to local filesystem",
    )
    def upload(self, file, file_size, dst, progress=None):
        """Upload a file or directory to the local filesystem in chunks of size
        `settings.BACKUP_UPLOAD_CHUNK_SIZE`.

        Args:
            file (file): The file to upload.
            file_size (int): The size of the file to upload.
            dst (str): The path to upload the file to.
            progress (dict): A dictionary of keyword arguments to pass to the tqdm
                progress bar.

        """
        logger = logging.getLogger(__name__)
        logger.info("uploading file to local filesystem: '%s'", dst)

        chunk_size = settings.BACKUP_UPLOAD_CHUNK_SIZE
        chunk_workers = settings.BACKUP_UPLOAD_CONCURRENCY

        if progress:
            progress = tqdm(**progress)

        with open(dst, "wb") as file_dst:
            with ThreadPoolExecutor(max_workers=chunk_workers) as executor:
                for chunk_offset in range(0, file_size, chunk_size):
                    chunk_length = min(chunk_size, file_size - chunk_offset)
                    executor.submit(
                        self.upload_chunk,
                        file,
                        file_dst,
                        chunk_offset,
                        chunk_length,
                        chunk_size,
                        progress,
                    )

    @log_execution(
        __name__,
        prefix="deleted file from local filesystem",
    )
    def delete(self, path):
        """Delete a file from the local filesystem.

        Args:
            path (str): The path to the file to delete.

        """
        logger = logging.getLogger(__name__)
        logger.debug("deleting file from local filesystem: '%s'", path)

        os.remove(
            path,
        )

    def list(self, path):
        """List all sorted files in the local filesystem at the specified path.

        The files are sorted so that the most recent files are listed first.

        Args:
            path (str): The path to list files from.

        Returns:
            List[str]: A list of file names within the specified path.

        """
        logger = logging.getLogger(__name__)
        logger.debug("listing files in local filesystem: '%s'", path)

        # we split listed files so the extension is ignored when sorting, this
        # makes it so that files with different extensions aren't ordered incorrectly
        # in the case where backup configurations change.

        return sorted(
            [os.path.join(path, i) for i in os.listdir(path)],
            key=lambda f: os.path.splitext(f)[0].lower(),
            reverse=True,
        )
