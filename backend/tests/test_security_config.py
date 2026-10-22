import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_defaults_and_debug():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENV="production", DEBUG=True, JWT_SECRET="CHANGE_ME_IN_PRODUCTION")


def test_optional_integrations_can_remain_disabled_in_production():
    value = Settings(
        _env_file=None, ENV="production", DEBUG=False, JWT_SECRET="x" * 64,
        GOOGLE_OAUTH_ENABLED=False, PAYMENTS_ENABLED=False, AI_ENABLED=False,
        EMAIL_ENABLED=False, FIRST_ADMIN_ENABLED=False,
    )
    assert value.ENV == "production"


def test_enabled_provider_requires_its_secrets():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, ENV="production", DEBUG=False, JWT_SECRET="x" * 64,
            PAYMENTS_ENABLED=True, PAYMENT_PROVIDER="stripe",
        )
