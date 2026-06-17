from jobhunt.settings import Settings


def test_settings_defaults_to_sqlite_database():
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./jobhunt.db"


def test_adzuna_is_disabled_when_credentials_are_missing():
    settings = Settings(adzuna_app_id="", adzuna_app_key="")
    assert settings.has_adzuna_credentials is False


def test_adzuna_is_enabled_when_credentials_are_present():
    settings = Settings(adzuna_app_id="app", adzuna_app_key="key")
    assert settings.has_adzuna_credentials is True
