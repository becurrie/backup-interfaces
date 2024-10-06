import logging
import os
import threading
from typing import List

import paramiko
from pydantic import BaseModel

from backup.config.models import BackupInterfaceConfig, DirectoryConfig
from backup.interfaces.interface import BackupInterface, ClientInterfaceMixin
from backup.utils import format_object, get_backup_name


class SSHDirectoryBackupInterfaceConfig(BackupInterfaceConfig):
    ssh_host: str
    ssh_username: str
    ssh_private_key: str
    ssh_port: int
    directories: List[DirectoryConfig]


class SSHDirectoryBackupInterface(ClientInterfaceMixin, BackupInterface):
    """Concrete implementation of a backup interface for backing up directories
    located on a remote machine via SSH.

    This class provides methods for backing up directories located on a remote machine
    via SSH. It manages the process of creating an archive of the specified directories
    on the remote machine and downloading the archive to the local machine for storage
    using the configured storage interface.

    It should be noted, this interface opens up an SFTP connection to the remote machine
    to transfer the archive files, so the remote machine must have an SSH server running
    and accessible to the application, this saves us from having to transfer the archived file
    from the remote machine to the local machine, and then to the storage interface, we use the
    SFTP connection to transfer the archive directly to the storage interface from the remote machine.

    Settings:

    - ssh_host (str): The hostname or IP address of the remote machine.
        This is the hostname or IP address of the remote machine that the interface will connect to
        via SSH to back up the specified directories.

    - ssh_username (str): The username to use for the SSH connection.
        This is the username that the interface will use to authenticate with the remote machine.

    - ssh_private_key (str): The path to the private key file for the SSH connection.
        This is the path to the private key file that the interface will use to authenticate with
        the remote machine. The private key file must be accessible to the application.

    - ssh_port (int): The port to use for the SSH connection.
        This is the port that the interface will use to connect to the remote machine via SSH.

    - directories (List[DirectoryConfig]): A list of directories to back up.
        This is a list of directories to back up on the remote machine. Each directory
        must have a source path on the remote machine and a destination path for the backup.

    """

    config_cls = SSHDirectoryBackupInterfaceConfig

    def _validate_directories(self):
        """Validate the directories to be backed up.

        This method checks that the directories to be backed up exist on the
        remote machine and that the application has the necessary
        permissions to read the directories.

        Raises:
            ValueError: If any specified directories are missing or inaccessible.

        """
        logger = logging.getLogger(__name__)
        logger.info("validating remote source directories")

        ls_cmd = "ls %s"
        test_cmd = "test -r %s"

        for directory in self.config.directories:
            stdin, stdout, stderr = self.client.exec_command(ls_cmd % directory.src)
            status = stdout.channel.recv_exit_status()

            if status != 0:
                raise ValueError(
                    "directory: '%s' does not exist on the remote machine"
                    % directory.src,
                )

            stdin, stdout, stderr = self.client.exec_command(test_cmd % directory.src)
            status = stdout.channel.recv_exit_status()

            if status != 0:
                raise ValueError(
                    "application does not have read access to directory: '%s'"
                    % directory.src,
                )

    def get_client(self):
        """Create a client object for the ssh connection.

        Returns:
            paramiko.SSHClient: An SSH client for the Azure Virtual Machine.

        Raises:
            Exception: If the client object cannot be created due to invalid
                configuration settings or connectivity issues.

        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.config.ssh_host,
            username=self.config.ssh_username,
            key_filename=self.config.ssh_private_key,
            port=self.config.ssh_port,
        )

        return client

    def validate(self):
        """Validate the ssh directory backup interface.

        Raises:
            ValueError: If any specified directories are missing or inaccessible.

        """
        self._validate_directories()

    def archive(self, src):
        """Create an archive file of the specified remote directory.

        This method creates an archive of the specified remote directory, which
        can then be uploaded to the configured storage interface.

        Args:
            src (str): The path to the directory to archive.

        Returns:
            Tuple[str, str]: A tuple containing the path to the archive file and
                the extension of the archive file.

        """
        logger = logging.getLogger(__name__)
        logger.info("creating archive of remote directory: '%s'", src)

        dst = "/tmp/%s.tar.gz" % os.path.basename(src)
        cmd = "tar -czf %s %s" % (dst, src)

        logger.debug("running command: '%s'", cmd)

        stdin, stdout, stderr = self.client.exec_command(cmd)
        stdout.channel.recv_exit_status()

        return dst, ".".join(dst.rsplit(".")[1:])

    def retention(self, directory, retention):
        """Handle the retention policy for the specified directory.

        This method handles the retention policy for the specified directory
        by removing any backups that exceed the specified retention period

        Args:
            directory (str): The path to the directory to apply the retention policy to.
            retention (int): The number of backups to retain.

        """
        logger = logging.getLogger(__name__)
        logger.info("applying retention policy to remote directory: '%s'", directory)

        ls_cmd = "ls -t %s"
        rm_cmd = "rm -r %s"

        stdin, stdout, stderr = self.client.exec_command(ls_cmd % directory)
        backups = stdout.read().decode().split("\n")

        if len(backups) > retention:
            for backup in backups[retention:]:
                logger.info("removing backup: '%s'", backup)
                stdin, stdout, stderr = self.client.exec_command(rm_cmd % backup)
                stdout.channel.recv_exit_status()

    def backup(self):
        """Perform the backup process for directories within a remote machine using ssh.

        This method acts as the entry point for the backup process. It connects to the
        remote machine using ssh, creates a backup of the specified directories, and
        stores the backup in the configured storage interface.

        For ssh directory backups, the directories are first compressed into a tar.gz
        archive, and then uploaded to the storage interface, where they are stored
        as individual files.

        When the backup is complete, the temporary tar.gz archive is removed from the
        remote machine to free up disk space.

        """
        logger = logging.getLogger(__name__)
        logger.info("backing up remote directories with ssh")

        for directory in self.config.directories:

            logger.info("backup remote directory: %s", directory.src)
            logger.info("directory configuration: %s" % format_object(directory))

            src, dst, name = (
                directory.src,
                directory.dest,
                directory.name,
            )

            uniq_name = get_backup_name(name)

            dst = os.path.join(dst, name)
            dst_backup = os.path.join(dst, uniq_name) + ".tar.gz"

            if not self.storage.exists(path=dst):
                self.storage.create_directory(path=dst)

            src_tmp = "/tmp/%s.tar.gz" % name
            src_tar_command_args = []

            if directory.exclude:
                src_tar_command_args.extend(
                    ["--exclude=%s" % e for e in directory.exclude]
                )

            src_tar_command_args = " ".join(src_tar_command_args)
            src_tar_command = "tar -czf %s %s %s" % (
                src_tmp,
                src_tar_command_args,
                src,
            )

            logger.info("creating temporary backup of remote directory: '%s'", src_tmp)
            logger.debug("running command: '%s'", src_tar_command)

            stdin, stdout, stderr = self.client.exec_command(src_tar_command)
            stdout.channel.recv_exit_status()

            # use paramiko to open a sftp connection and stream the
            # backup to the storage interface.

            sftp = self.client.open_sftp()

            try:
                with sftp.file(src_tmp, "rb") as remote_file:

                    # get the size of the remote file to use for the progress bar.
                    # this is used to provide a progress bar when uploading the file.

                    remote_file_size = remote_file.stat().st_size
                    remote_file_progress = {
                        "total": remote_file_size,
                        "unit": "B",
                        "unit_scale": True,
                        "desc": "Uploading from remote directory",
                    }

                    self.storage.upload(
                        file=remote_file,
                        file_size=remote_file_size,
                        dst=dst_backup,
                        progress=remote_file_progress,
                    )

            finally:
                sftp.close()

            src_tmp_rm_command = "rm %s" % src_tmp

            logger.info("removing temporary backup of remote directory: '%s'", src_tmp)
            logger.debug("running command: '%s'", src_tmp_rm_command)

            stdin, stdout, stderr = self.client.exec_command("rm %s" % src_tmp)
            stdout.channel.recv_exit_status()

            # finally, we can deal with retention (if it's enabled) for the storage
            # interface. we will remove any backups that exceed the specified retention
            # period.

            if directory.retention:
                self.storage.retention(
                    path=dst,
                    retention=directory.retention,
                )
