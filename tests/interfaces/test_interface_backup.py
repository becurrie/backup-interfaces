import pydantic
import pytest

from backup.config.models import BaseInterfaceConfig, StorageInterfaceConfig
from tests.fixtures.interfaces import MockBackupInterface, MockStorageInterface


def test_interface_backup_no_storage():
    """Test that the backup interface class can not be created without a storage interface."""
    with pytest.raises(TypeError):
        MockBackupInterface(
            {
                "interface": "tests.fixtures.interfaces.MockBackupInterface",
                "string": "test",
                "integer": 123,
                "boolean": True,
            }
        )


def test_interface_backup_with_storage():
    """Test that the backup interface class can be created with a storage interface."""
    storage = MockStorageInterface(
        {
            "interface": "tests.fixtures.interfaces.MockStorageInterface",
            "string": "test",
            "integer": 123,
            "boolean": True,
        }
    )
    interface = MockBackupInterface(
        {
            "interface": "tests.fixtures.interfaces.MockBackupInterface",
            "string": "test",
            "integer": 123,
            "boolean": True,
        },
        storage=storage,
    )
    assert interface.storage == storage
