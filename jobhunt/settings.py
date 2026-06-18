from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        populate_by_name=True,
    )

    env: str = Field(default="development", validation_alias="JOBHUNT_ENV")
    database_url: str = Field(
        default="sqlite:///./jobhunt.db",
        validation_alias="JOBHUNT_DATABASE_URL",
    )
    log_level: str = Field(default="INFO", validation_alias="JOBHUNT_LOG_LEVEL")

    adzuna_app_id: str = Field(default="", validation_alias="ADZUNA_APP_ID")
    adzuna_app_key: str = Field(default="", validation_alias="ADZUNA_APP_KEY")

    usajobs_email: str = Field(default="", validation_alias="USAJOBS_EMAIL")
    usajobs_api_key: str = Field(default="", validation_alias="USAJOBS_API_KEY")

    reed_api_key: str = Field(default="", validation_alias="REED_API_KEY")

    # Groq (free LLM API) for the CV-based profile builder.
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile", validation_alias="GROQ_MODEL"
    )

    # Where the active candidate profile is stored (personal data; git-ignored).
    profile_path: str = Field(
        default="config/candidate_profile.yaml", validation_alias="JOBHUNT_PROFILE_PATH"
    )

    @property
    def has_groq_credentials(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_adzuna_credentials(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @property
    def has_usajobs_credentials(self) -> bool:
        return bool(self.usajobs_email and self.usajobs_api_key)

    @property
    def has_reed_credentials(self) -> bool:
        return bool(self.reed_api_key)
