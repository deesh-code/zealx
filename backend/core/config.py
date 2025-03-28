"""
Configuration settings for ZealX Backend.
Handles environment variables and settings for Cloudflare API keys,
database connections, and Adaptive Execution Mode (ADX) parameters.

For production cloud hosting, this uses secure environment variable handling
and includes cloud-specific configurations.
"""

import os
import secrets
from typing import List, Dict, Optional, Any, Union
from pydantic import Field, AnyHttpUrl,field_validator
from pydantic_settings.main import BaseSettings
import json
from functools import lru_cache

class CloudflareSettings(BaseSettings):
    """Cloudflare API settings."""
    api_keys: List[str] = Field(..., env="CLOUDFLARE_API_KEYS")
    account_ids: List[str] = Field(..., env="CLOUDFLARE_ACCOUNT_IDS")
    worker_urls: List[str] = Field(..., env="CLOUDFLARE_WORKER_URLS")
    
    @field_validator("api_keys", "account_ids", "worker_urls")
    def parse_list(cls, v):
        """Parse comma-separated list from environment variables."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    host: str = Field("localhost", env="POSTGRES_HOST")
    port: str = Field("5432", env="POSTGRES_PORT")
    user: str = Field(..., env="POSTGRES_USER")
    password: str = Field(..., env="POSTGRES_PASSWORD")
    db: str = Field(..., env="POSTGRES_DB")
    min_connections: int = Field(1, env="POSTGRES_MIN_CONNECTIONS")
    max_connections: int = Field(10, env="POSTGRES_MAX_CONNECTIONS")
    
    @property
    def sqlalchemy_uri(self) -> str:
        """Get SQLAlchemy connection URI."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
    
    @property
    def asyncpg_uri(self) -> str:
        """Get asyncpg connection URI."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class RedisSettings(BaseSettings):
    """Redis connection settings."""
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")
    use_ssl: bool = Field(False, env="REDIS_USE_SSL")
    
    @property
    def url(self) -> str:
        """Get Redis connection URL."""
        protocol = "rediss" if self.use_ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth}{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class ADXSettings(BaseSettings):
    """Adaptive Execution Mode (ADX) settings."""
    enabled: bool = Field(True, env="ADX_ENABLED")
    monitoring_interval: int = Field(60, env="ADX_MONITORING_INTERVAL")  # seconds
    max_monitoring_interval: int = Field(300, env="ADX_MAX_MONITORING_INTERVAL")  # seconds
    idle_timeout: int = Field(300, env="ADX_IDLE_TIMEOUT")  # seconds
    cpu_threshold: float = Field(80.0, env="ADX_CPU_THRESHOLD")  # percentage
    memory_threshold: float = Field(80.0, env="ADX_MEMORY_THRESHOLD")  # percentage
    battery_threshold: float = Field(20.0, env="ADX_BATTERY_THRESHOLD")  # percentage
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class SecuritySettings(BaseSettings):
    """Security settings."""
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_bcrypt_rounds: int = Field(12, env="PASSWORD_BCRYPT_ROUNDS")
    
    # API security
    api_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="API_KEY")
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    allowed_hosts: List[str] = Field(["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_default: int = Field(100, env="RATE_LIMIT_DEFAULT")  # requests per minute
    burst_limit_default: int = Field(5, env="BURST_LIMIT_DEFAULT")  # concurrent requests
    
    @field_validator("cors_origins", "allowed_hosts")
    def parse_list(cls, v):
        """Parse comma-separated list from environment variables."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class APIAccountManagerSettings(BaseSettings):
    """API Account Manager settings."""
    health_check_interval: int = Field(60, env="API_HEALTH_CHECK_INTERVAL")  # seconds
    max_retries: int = Field(3, env="API_MAX_RETRIES")
    timeout: float = Field(5.0, env="API_TIMEOUT")  # seconds
    cache_ttl: int = Field(300, env="API_CACHE_TTL")  # seconds
    
    # Failover settings
    failover_enabled: bool = Field(True, env="API_FAILOVER_ENABLED")
    failover_threshold: int = Field(2, env="API_FAILOVER_THRESHOLD")  # consecutive failures
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class LoggingSettings(BaseSettings):
    """Logging settings."""
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    log_to_file: bool = Field(True, env="LOG_TO_FILE")
    log_dir: str = Field("logs", env="LOG_DIR")
    max_size: int = Field(10 * 1024 * 1024, env="LOG_MAX_SIZE")  # 10 MB
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class CloudSettings(BaseSettings):
    """Cloud-specific settings."""
    provider: str = Field("aws", env="CLOUD_PROVIDER")  # aws, gcp, azure
    region: str = Field("us-east-1", env="CLOUD_REGION")
    instance_type: str = Field("t3.small", env="CLOUD_INSTANCE_TYPE")
    use_load_balancer: bool = Field(True, env="CLOUD_USE_LOAD_BALANCER")
    auto_scaling: bool = Field(True, env="CLOUD_AUTO_SCALING")
    min_instances: int = Field(1, env="CLOUD_MIN_INSTANCES")
    max_instances: int = Field(5, env="CLOUD_MAX_INSTANCES")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class Settings(BaseSettings):
    """Main application settings."""
    # App settings
    app_name: str = Field("ZealX Backend", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    environment: str = Field("development", env="ENVIRONMENT")  # development, staging, production
    
    # Component settings
    cloudflare: CloudflareSettings = CloudflareSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    adx: ADXSettings = ADXSettings()
    security: SecuritySettings = SecuritySettings()
    api_manager: APIAccountManagerSettings = APIAccountManagerSettings()
    logging: LoggingSettings = LoggingSettings()
    cloud: CloudSettings = CloudSettings()
    
    # Storage settings
    storage_path: str = Field("/data/zealx", env="STORAGE_PATH")
    max_storage_size: int = Field(10 * 1024 * 1024 * 1024, env="MAX_STORAGE_SIZE")  # 10 GB
    
    # Convenience properties
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return self.redis.url
    
    @property
    def allowed_hosts(self) -> List[str]:
        """Get allowed hosts."""
        return self.security.allowed_hosts
    
    @validator("storage_path")
    def validate_storage_path(cls, v):
        """Validate storage path for cloud environments."""
        # For AWS, use EFS mount point
        if os.getenv("CLOUD_PROVIDER") == "aws":
            return os.getenv("AWS_EFS_MOUNT_POINT", v)
        # For GCP, use persistent disk mount point
        elif os.getenv("CLOUD_PROVIDER") == "gcp":
            return os.getenv("GCP_PD_MOUNT_POINT", v)
        # For Azure, use Azure Files mount point
        elif os.getenv("CLOUD_PROVIDER") == "azure":
            return os.getenv("AZURE_FILES_MOUNT_POINT", v)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Create settings instance
settings = get_settings()
