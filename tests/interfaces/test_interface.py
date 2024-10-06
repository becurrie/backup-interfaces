import pydantic
import pytest

from backup.config.models import BaseInterfaceConfig
from backup.interfaces.interface import ClientInterfaceMixin, Interface
from tests.fixtures.interfaces import (
    MockClientInterface,
    MockInterface,
    MockInterfaceConfig,
)


def test_interface_concrete_with_pydantic_model():
    """Test that the interface class can be created with a pydantic configuration."""
    assert MockInterface(
        config=MockInterfaceConfig(
            interface="tests.interfaces.test_interface.MockInterface",
            string="test",
            integer=123,
            boolean=True,
        )
    )


def test_interface_concrete_with_dict():
    """Test that the interface class can be created with a dictionary."""
    assert MockInterface(
        {
            "interface": "tests.fixtures.interfaces.MockInterface",
            "string": "test",
            "integer": 123,
            "boolean": True,
        }
    )


def test_interface_concrete_with_invalid_dict():
    """Test that the interface class raises an error when the configuration is invalid."""
    with pytest.raises(pydantic.ValidationError):
        MockInterface(
            {
                "interface": "tests.fixtures.interfaces.MockInterface",
                "string": "test",
                "integer": 123,
            }
        )


def test_interface_concrete_client_mixin():
    """Test that a concrete interface that uses the client interface mixin can be created."""
    interface = MockClientInterface(
        {
            "interface": "tests.fixtures.interfaces.MockClientInterface",
            "string": "test",
            "integer": 123,
            "boolean": True,
        }
    )

    assert interface.client == "client"
