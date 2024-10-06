from backup.config.models import (
    BackupInterfaceConfig,
    BaseInterfaceConfig,
    StorageInterfaceConfig,
    VaultInterfaceConfig,
)
from backup.interfaces.interface import (
    BackupInterface,
    ClientInterfaceMixin,
    Interface,
    StorageInterface,
    VaultInterface,
)


class MockInterfaceConfig(BaseInterfaceConfig):
    string: str
    integer: int
    boolean: bool


class MockBackupInterfaceConfig(BackupInterfaceConfig):
    string: str
    integer: int
    boolean: bool


class MockStorageInterfaceConfig(StorageInterfaceConfig):
    string: str
    integer: int
    boolean: bool


class MockVaultInterfaceConfig(VaultInterfaceConfig):
    pass


class MockInterface(Interface):
    config_cls = MockInterfaceConfig


class MockClientInterface(ClientInterfaceMixin, MockInterface):
    def get_client(self):
        return "client"


class MockBackupInterface(BackupInterface):
    config_cls = MockBackupInterfaceConfig

    def validate(self):
        return "validate"

    def archive(self, src):
        return "archive"

    def backup(self):
        return "backup"


class MockStorageInterface(StorageInterface):
    config_cls = MockStorageInterfaceConfig

    def create(self, path):
        return "create"

    def exists(self, path):
        return "exists"

    def upload_chunk(self, *args, **kwargs):
        return "upload_chunk"

    def upload(self, file, file_size, dst):
        return "upload"

    def delete(self, path):
        return "delete"

    def list(self, path):
        return "list"


class MockVaultInterface(VaultInterface):
    config_cls = MockVaultInterfaceConfig

    def get_secret(self, secret_name):
        return secret_name
