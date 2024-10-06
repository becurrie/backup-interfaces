from unittest.mock import MagicMock

import pydantic
import pytest

from backup.config.models import BaseInterfaceConfig, StorageInterfaceConfig
from tests.fixtures.interfaces import MockBackupInterface, MockStorageInterface


@pytest.fixture
def mock_storage():
    """Fixture to create a mock storage interface"""
    storage = MockStorageInterface(
        {
            "interface": "tests.fixtures.interfaces.MockStorageInterface",
            "string": "test",
            "integer": 123,
            "boolean": True,
        }
    )
    storage.list = MagicMock()
    storage.delete = MagicMock()

    return storage


@pytest.fixture
def mock_retention_config():
    """Fixture to create a mock retention configuration."""
    config = MagicMock()
    config.count = 3

    return config


def test_interface_storage_default_retention(mock_storage, mock_retention_config):
    """Test that default retention works as expected with a storage interface."""
    mock_storage.list.return_value = [
        "backup1",
        "backup2",
        "backup3",
        "backup4",
        "backup5",
    ]
    mock_storage.retention(
        path="/test/backup",
        config=mock_retention_config,
    )

    assert mock_storage.delete.call_count == 2

    mock_storage.delete.assert_any_call("backup4")
    mock_storage.delete.assert_any_call("backup5")
