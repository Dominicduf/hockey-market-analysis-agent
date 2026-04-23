from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str
    model_name: str = "deepseek/deepseek-chat"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    max_context_tokens: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
