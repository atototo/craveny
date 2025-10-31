"""
Craveny 애플리케이션 설정 관리
모든 환경 변수는 이 파일을 통해 접근
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""

    # 애플리케이션
    APP_NAME: str = "Craveny"
    DEBUG: bool = False

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "craveny"

    @property
    def DATABASE_URL(self) -> str:
        """SQLAlchemy용 데이터베이스 URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        """Celery용 Redis URL"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # 텔레그램
    TELEGRAM_BOT_TOKEN: str

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # 로깅
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "data/logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 객체 (싱글톤)
settings = Settings()
