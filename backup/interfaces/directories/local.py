import logging
import os
import platform
import shutil
import tarfile
from typing import List

from backup.config.models import BackupInterfaceConfig, DirectoryConfig
from backup.decorators import log_execution
from backup.interfaces.interface import BackupInterface
from backup.utils import format_object, get_backup_name


class LocalDirectoryBackupInterfaceConfig(BackupInterfaceConfig):
    directories: List[DirectoryConfig]


class LocalDirectoryBackupInterface(BackupInterface):
    """Concrete implementation of a backup interface for backing up directories
    located on the local machine.

    This class provides methods for backing up directories located on the local machine.
    It manages the process of creating an archive of the specified directories and uploading
    the archive to the configured storage interface.

    No additional setup is required to get local directory backups working.

    Settings:

    - directories (List[DirectoryConfig]): A list of directories to back up.
        This is a list of directories to back up on the local machine. Each directory
        must have a source path on the local machine and a destination path for the backup.

    """

    config_cls = LocalDirectoryBackupInterfaceConfig

    def _validate_directories(self):
        """Validate the directories to be backed up.

        This method checks that the directories to be backed up exist on the
        local machine that the backup process is running on, and that the application
        has the necessary permissions to read the directories.

        Raises:
            ValueError: If any specified directories are missing or inaccessible.

        """
        logger = logging.getLogger(__name__)
        logger.info("validating local source directories")

        for directory in self.config.directories:
            if not os.path.exists(directory.src):
                raise ValueError(
                    "directory: %s does not exist on the local machine" % directory.src,
                )
            if not os.access(directory.src, os.R_OK):
                raise ValueError(
                    "application does not have read access to directory: %s"
                    % directory.src
                )

    def validate(self):
        """Validate the local directory backup interface.

        Raises:
            ValueError: If any specified directories are missing or inaccessible.

        """
        self._validate_directories()

    @log_execution(
        __name__,
        prefix="created archive of local directory",
    )
    def archive(self, src):
        """Create an archive file of the specified local directory.

        This method creates an archive of the specified local directory, which
        can then be uploaded to the configured storage interface.

        Args:
            src (str): The path to the directory to archive.

        Returns:
            Tuple[str, str]: A tuple containing the path to the archive file and
                the extension of the archive file.

        """
        logger = logging.getLogger(__name__)
        logger.info("creating archive of local directory: '%s'", src)

        file = shutil.make_archive(
            base_name=src,
            root_dir=src,
            format="gztar",
        )

        return file, ".".join(file.rsplit(".")[1:])

    def backup(self):
        """Backup the specified local directories.

        This method acts as the entry point for the local directory backup interface,
        and is responsible for backing up the specified directories to the configured
        storage interface.

        For local directory backups, the directories are first compressed into a zip
        archive, and then uploaded to the storage interface, where they are stored
        as individual files.

        When the backup is complete, the temporary zip archive is removed from the
        local machine to free up disk space.

        """
        logger = logging.getLogger(__name__)
        logger.debug("backing up local directories")

        for directory in self.config.directories:
            logger.info("backing up directory: '%s'", directory.src)
            logger.debug("directory configuration: %s" % format_object(directory))

            src, dst, name = (
                directory.src,
                directory.dest,
                directory.name,
            )

            file, extension = (
                shutil.make_archive(
                    base_name=src,
                    root_dir=src,
                    format="gztar",
                ),
                "tar.gz",
            )

            dst_name = get_backup_name(name)
            dst = os.path.join(dst, name)
            dst_backup = os.path.join(dst, dst_name + ".%s" % extension)

            if not self.storage.exists(path=dst):
                self.storage.create_directory(path=dst)

            with open(archive, "rb") as file_obj:

                # get the size of the local file to use for the progress bar.
                # this is used to provide a progress bar when uploading the file.

                file_obj_size = os.path.getsize(archive)
                file_obj_progress = {
                    "total": file_obj_size,
                    "unit": "B",
                    "unit_scale": True,
                    "desc": "Uploading from local directory",
                }

                self.storage.upload(
                    file=file_obj,
                    file_size=file_obj_size,
                    dst=dst_backup,
                    progress=file_obj_progress,
                )

            logger.info("removing temporary archive of local directory: '%s'", archive)

            # since this is just a local directory backup, we can simply use the
            # os.remove method to delete the temporary archive file.

            os.remove(archive)

            # finally, we can deal with retention (if it's enabled) for the storage
            # interface. we will remove any backups that exceed the specified retention
            # period.

            if directory.retention:
                self.storage.retention(
                    path=dst,
                    retention=directory.retention,
                )
