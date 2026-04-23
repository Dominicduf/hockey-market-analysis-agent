from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str
    model_name: str = "deepseek/deepseek-chat"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    max_context_tokens: int = 8000
    agent_timeout: int = 300
    max_recursion: int = 25
    max_retries: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
