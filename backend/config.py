from pydantic import BaseSettings, AnyUrl


class Settings(BaseSettings):
    mongo_client_url: AnyUrl
    redis_server_url: AnyUrl

    class Config:
        env_file = "./.env"
