import re

import pytest

from backup.utils import (
    format_object,
    get_backup_name,
    get_class,
    mask_sensitive_data,
    to_bool,
    to_upper,
)
from tests.fixtures import module


class TestClass:
    pass


def test_to_bool():
    """Test that the to_bool function converts a string to a boolean."""
    assert to_bool("true") is True
    assert to_bool("false") is False
    assert to_bool("True") is True
    assert to_bool("False") is False
    assert to_bool("1") is True
    assert to_bool("0") is False
    assert to_bool("yes") is True
    assert to_bool("no") is False
    assert to_bool("on") is True
    assert to_bool("off") is False


def test_to_upper():
    """Test that the to_upper function converts a string to uppercase."""
    assert to_upper("hello, world!") == "HELLO, WORLD!"


def test_get_class_success():
    """Test that the get_class function can import a class from a module."""
    assert get_class("tests.utils.test_utils.TestClass") == TestClass


def test_get_class_invalid_module():
    """Test that the get_class function raises an ImportError when the module
    cannot be imported.
    """
    with pytest.raises(ImportError):
        get_class("tests.utils.module_does_not_exist.TestClass")


def test_get_class_invalid_class():
    """Test that the get_class function raises an ImportError when the class
    cannot be found in the imported module.
    """
    with pytest.raises(ImportError):
        get_class("tests.utils.test_utils.TestClassDoesNotExist")


def test_get_backup_name():
    """Test that the get_backup_name function returns the correct backup name."""
    name = get_backup_name("test")

    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}", name) is not None
    assert "." not in name


def test_mask_sensitive_data():
    """Test that the mask_sensitive_data function masks sensitive data in a string."""
    # simple dict.
    assert mask_sensitive_data({"password": "secret"}) == {"password": "********"}
    # nested dict.
    assert mask_sensitive_data({"api": {"key": "secret"}}) == {
        "api": {"key": "********"}
    }
    # nested list.
    assert mask_sensitive_data({"api": [{"key": "secret"}]}) == {
        "api": [{"key": "********"}]
    }
    # simple data (like a string present).
    assert mask_sensitive_data({"password": "secret", "scopes": ["read", "write"]}) == {
        "password": "********",
        "scopes": ["read", "write"],
    }


def test_format_object():
    """Test that the format_object function formats objects as a string."""
    assert format_object(module) == "\n'MODULE_VAR_ONE': 1, 'MODULE_VAR_TWO': 2"
