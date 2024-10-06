import pytest

from backup.config.models import BaseModelExtra


def test_extra_model_fields(monkeypatch):
    """Test that the BaseModelExtra class allows extra fields to be set on the
    model instance.
    """

    class TestModel(BaseModelExtra):
        string: str
        integer: int

    model = TestModel(
        string="test string",
        integer=123,
        extra_value="extra value",
    )

    assert model.extra_value == "extra value"
