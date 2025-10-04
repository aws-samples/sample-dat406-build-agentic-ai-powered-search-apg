"""
Configuration management for DAT406 Workshop Backend

Uses Pydantic Settings for environment variable validation and type safety.
All configuration is loaded from environment variables or .env file.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Environment variables can be set in .env file or system environment.
    """
    
    # ========================================
    # Database Configuration
    # ========================================
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # Optional: Full database URL (constructed if not provided)
    DATABASE_URL: Optional[str] = None
    
    # Optional: AWS Secrets Manager ARN for database credentials
    DB_SECRET_ARN: Optional[str] = None
    
    # Optional: Aurora cluster ARN for RDS Data API
    DB_CLUSTER_ARN: Optional[str] = None
    
    # ========================================
    # AWS Configuration
    # ========================================
    AWS_REGION: str = "us-west-2"
    AWS_DEFAULT_REGION: Optional[str] = None
    
    # ========================================
    # Bedrock Model Configuration
    # ========================================
    # Embedding model for semantic search
    BEDROCK_EMBEDDING_MODEL: str = "amazon.titan-embed-text-v2:0"
    
    # Chat model for conversational features
    BEDROCK_CHAT_MODEL: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    
    # ========================================
    # Application Configuration
    # ========================================
    # API settings
    API_VERSION: str = "1.0.0"
    API_TITLE: str = "DAT406 Workshop API"
    API_DESCRIPTION: str = "Semantic Search API powered by Amazon Aurora PostgreSQL and Bedrock"
    
    # CORS settings
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True  # Auto-reload in development
    
    # ========================================
    # Database Pool Configuration
    # ========================================
    # Connection pool settings for psycopg
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    DB_POOL_TIMEOUT: int = 30  # seconds
    DB_CONNECT_TIMEOUT: int = 10  # seconds
    
    # ========================================
    # Search Configuration
    # ========================================
    # Default number of search results
    DEFAULT_SEARCH_LIMIT: int = 20
    MAX_SEARCH_LIMIT: int = 100
    
    # Vector search parameters
    VECTOR_SIMILARITY_THRESHOLD: float = 0.0  # Minimum similarity score
    
    # ========================================
    # Performance & Caching
    # ========================================
    # Enable query result caching (future feature)
    ENABLE_CACHE: bool = False
    CACHE_TTL: int = 300  # seconds
    
    # ========================================
    # Logging Configuration
    # ========================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ========================================
    # Development & Debugging
    # ========================================
    DEBUG: bool = False
    DEVELOPMENT_MODE: bool = True
    
    # Show SQL queries in logs
    SHOW_SQL: bool = False
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",  # Allow extra environment variables
    )
    
    # ========================================
    # Computed Properties
    # ========================================
    
    @property
    def database_url(self) -> str:
        """
        Construct PostgreSQL connection URL.
        
        Returns:
            str: Full database connection URL
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def async_database_url(self) -> str:
        """
        Construct async PostgreSQL connection URL.
        
        Returns:
            str: Async database connection URL for psycopg 3
        """
        return self.database_url.replace("postgresql://", "postgresql://")
    
    @property
    def aws_region_resolved(self) -> str:
        """
        Get AWS region, preferring AWS_REGION over AWS_DEFAULT_REGION.
        
        Returns:
            str: AWS region name
        """
        return self.AWS_REGION or self.AWS_DEFAULT_REGION or "us-west-2"
    
    @property
    def is_production(self) -> bool:
        """
        Check if running in production mode.
        
        Returns:
            bool: True if production mode
        """
        return not self.DEVELOPMENT_MODE and not self.DEBUG
    
    @property
    def cors_origins_list(self) -> list[str]:
        """
        Get CORS origins as list.
        
        Returns:
            list[str]: List of allowed CORS origins
        """
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses LRU cache to ensure settings are loaded only once.
    This is the recommended way to access settings throughout the application.
    
    Returns:
        Settings: Application settings instance
        
    Example:
        ```python
        from config import get_settings
        
        settings = get_settings()
        print(settings.DATABASE_URL)
        ```
    """
    return Settings()


# Convenience export
settings = get_settings()


# ========================================
# Configuration Validation
# ========================================

def validate_config() -> None:
    """
    Validate configuration at startup.
    
    Raises:
        ValueError: If configuration is invalid
    """
    settings = get_settings()
    
    # Validate database configuration
    if not settings.DB_HOST:
        raise ValueError("DB_HOST is required")
    
    if not settings.DB_NAME:
        raise ValueError("DB_NAME is required")
    
    if not settings.DB_USER:
        raise ValueError("DB_USER is required")
    
    if not settings.DB_PASSWORD:
        raise ValueError("DB_PASSWORD is required")
    
    # Validate AWS configuration
    if not settings.AWS_REGION:
        raise ValueError("AWS_REGION is required")
    
    # Validate pool sizes
    if settings.DB_POOL_MIN_SIZE > settings.DB_POOL_MAX_SIZE:
        raise ValueError("DB_POOL_MIN_SIZE cannot exceed DB_POOL_MAX_SIZE")
    
    # Validate search limits
    if settings.DEFAULT_SEARCH_LIMIT > settings.MAX_SEARCH_LIMIT:
        raise ValueError("DEFAULT_SEARCH_LIMIT cannot exceed MAX_SEARCH_LIMIT")
    
    print("✅ Configuration validated successfully")


if __name__ == "__main__":
    # Test configuration loading
    validate_config()
    
    settings = get_settings()
    print("\n" + "="*70)
    print("DAT406 Workshop - Configuration Summary")
    print("="*70)
    print(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"AWS Region: {settings.aws_region_resolved}")
    print(f"Embedding Model: {settings.BEDROCK_EMBEDDING_MODEL}")
    print(f"Chat Model: {settings.BEDROCK_CHAT_MODEL}")
    print(f"API Version: {settings.API_VERSION}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Development Mode: {settings.DEVELOPMENT_MODE}")
    print("="*70)