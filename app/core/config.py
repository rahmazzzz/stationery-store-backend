from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_secret_key: str
    supabase_publishable_key: str

    admin_user_ids: str
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def admin_user_id_set(self) -> set[str]:
        """Return configured admin IDs as a set."""
        return {
            user_id.strip()
            for user_id in self.admin_user_ids.split(",")
            if user_id.strip()
        }


settings = Settings()
