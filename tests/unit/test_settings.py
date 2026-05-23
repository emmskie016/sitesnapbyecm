from app.settings import settings


def test_settings_loads_from_env():
    assert settings.anthropic_api_key == "test-anthropic"
    assert settings.r2_bucket == "test-bucket"
    assert settings.env == "test"


def test_settings_has_defaults():
    assert settings.log_level == "INFO"
