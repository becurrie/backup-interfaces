import os

import pydantic
import pytest
import yaml

from backup.config.loader import (
    load_config,
    load_vault,
    load_yaml,
    sub_env_vars,
    sub_yaml,
)


@pytest.fixture
def preserve_environment():
    """Fixture to preserve the environment in between tests."""
    original = os.environ.copy()

    # yield to run our test...
    # ...then restore the environment
    yield

    os.environ.clear()
    os.environ.update(original)


def write_config(tmp_path, config, filename="config.yaml"):
    """Write a configuration to a file.

    Args:
        tmp_path (Path): Temporary directory path.
        config (dict): Configuration dictionary.
        filename (str): Configuration file name.

    Returns:
        The path to the temporary file.

    """
    with open(tmp_path / filename, "w") as file:
        yaml.dump(config, file)

    return tmp_path / filename


def test_load_config_no_path():
    """Test loading configuration without a path raises an error."""
    with pytest.raises(ValueError) as exc_info:
        load_config(path=None)

    assert str(exc_info.value) == (
        "configuration file path not set, please ensure the "
        "'BACKUP_CONFIG_PATH' "
        "environment variable is set to a valid configuration file path."
    )


def test_load_config_invalid_path(tmp_path):
    """Test loading configuration with an invalid path raises an error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_config(path=tmp_path / "invalid_path")

    assert str(exc_info.value) == (
        "configuration file not found at path: '%s'" % (tmp_path / "invalid_path")
    )


def test_load_config_invalid_config(tmp_path):
    """Test loading configuration with an invalid configuration raises an error.

    This test writes an invalid configuration to a file and attempts to load it, we
    expect our pydantic model to raise a validation error because the configuration
    is missing required fields.

    """
    with pytest.raises(pydantic.ValidationError):
        load_config(
            path=write_config(
                tmp_path,
                {
                    "key": "value",
                    "key2": "value2",
                },
            )
        )


def test_load_config_valid_config(tmp_path):
    """Test loading configuration with a valid configuration."""
    config = load_config(
        path=write_config(
            tmp_path,
            {
                "name": "test",
                "enabled": True,
                "storage": {
                    "interface": "tests.fixtures.interfaces.MockStorageInterface",
                },
                "interfaces": [
                    {
                        "interface": "tests.fixtures.interfaces.MockBackupInterface",
                        "enabled": True,
                    }
                ],
            },
        )
    )

    assert config.name == "test"
    assert config.enabled is True
    assert config.storage.interface == "tests.fixtures.interfaces.MockStorageInterface"
    assert config.interfaces[0].enabled is True
    assert (
        config.interfaces[0].interface
        == "tests.fixtures.interfaces.MockBackupInterface"
    )


def test_load_config_valid_vault(preserve_environment, tmp_path):
    """Test that loading a valid vault configuration works."""
    config = load_config(
        path=write_config(
            tmp_path,
            {
                "name": "test",
                "enabled": True,
                "storage": {
                    "interface": "local",
                },
                "vaults": [
                    {
                        "interface": "tests.fixtures.interfaces.MockVaultInterface",
                        "secrets": {
                            "ENV_ONE": "secret-name-one",
                            "ENV_TWO": "secret-name-two",
                        },
                    }
                ],
                "interfaces": [
                    {
                        "interface": "tests.fixtures.interfaces.MockBackupInterface",
                        "enabled": True,
                        "secret_one": "${ENV_ONE}",
                        "secret_two": "${ENV_TWO}",
                    },
                ],
            },
        )
    )

    assert config.interfaces[0].secret_one == "secret-name-one"
    assert config.interfaces[0].secret_two == "secret-name-two"


def test_load_config_invalid_environment_variable(
    preserve_environment, tmp_path, caplog
):
    """Test that loading a configuration with an invalid environment variable logs a warning."""
    load_config(
        path=write_config(
            tmp_path,
            {
                "name": "test",
                "enabled": True,
                "storage": {
                    "interface": "tests.fixtures.interfaces.MockStorageInterface",
                },
                "interfaces": [
                    {
                        "interface": "tests.fixtures.interfaces.MockBackupInterface",
                        "enabled": True,
                        "secret_one": "${ENV_ONE}",
                        "secret_two": "${ENV_TWO}",
                    },
                ],
            },
        )
    )

    assert len(caplog.records) == 2
    assert (
        "configuration contains reference to environment variable 'ENV_ONE' which is not set in the environment."
        in caplog.text
    )
    assert (
        "configuration contains reference to environment variable 'ENV_TWO' which is not set in the environment."
        in caplog.text
    )
