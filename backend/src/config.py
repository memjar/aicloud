"""
Configuration loader with AWS Secrets Manager integration.
Supports environment-specific configs (dev, staging, prod) with secure key management.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    pool_size: int = 20
    pool_recycle_seconds: int = 3600
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis/cache configuration."""
    url: str
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


@dataclass
class StripeConfig:
    """Stripe billing configuration."""
    api_key: str
    webhook_key: str
    api_version: str = "2023-10-16"


@dataclass
class LLMProvidersConfig:
    """LLM provider API keys."""
    openai_api_key: str
    anthropic_api_key: str
    together_api_key: str


@dataclass
class SecurityConfig:
    """Security-related configuration."""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_hour: int = 1000


@dataclass
class AWSConfig:
    """AWS configuration."""
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: str = "us-east-1"
    secrets_manager_enabled: bool = False
    secrets_manager_region: str = "us-east-1"
    secrets_manager_secret_name: str = "aimodels/api/keys"
    secrets_manager_secret_version_id: Optional[str] = None


@dataclass
class ObservabilityConfig:
    """Monitoring and logging configuration."""
    sentry_dsn: Optional[str] = None
    posthog_api_key: Optional[str] = None
    posthog_api_host: str = "https://us.posthog.com"
    cloudwatch_log_group: str = "/aimodels/api"
    cloudwatch_enabled: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""
    environment: str
    log_level: str = "INFO"
    api_port: int = 8000
    api_version: str = "v1"
    allowed_origins: list
    debug: bool = False
    reload: bool = False
    verbose: bool = False

    # Sub-configurations
    database: DatabaseConfig
    redis: RedisConfig
    stripe: StripeConfig
    llm_providers: LLMProvidersConfig
    security: SecurityConfig
    aws: AWSConfig
    observability: ObservabilityConfig


class SecretsManager:
    """Manages secret retrieval from multiple sources."""

    def __init__(self, aws_config: AWSConfig):
        self.aws_config = aws_config
        self._client = None
        self._cache = {}

    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve secret from AWS Secrets Manager or environment.

        Args:
            secret_name: Name/ARN of the secret

        Returns:
            Dictionary containing the secret
        """
        if not self.aws_config.secrets_manager_enabled:
            logger.debug(f"Secrets Manager disabled, using environment variables")
            return {}

        if secret_name in self._cache:
            return self._cache[secret_name]

        try:
            import boto3
            from botocore.exceptions import ClientError

            if not self._client:
                self._client = boto3.client(
                    'secretsmanager',
                    region_name=self.aws_config.secrets_manager_region,
                    aws_access_key_id=self.aws_config.access_key_id,
                    aws_secret_access_key=self.aws_config.secret_access_key,
                )

            kwargs = {
                'SecretId': secret_name,
            }
            if self.aws_config.secrets_manager_secret_version_id:
                kwargs['VersionId'] = self.aws_config.secrets_manager_secret_version_id

            response = self._client.get_secret_value(**kwargs)

            if 'SecretString' in response:
                secret = json.loads(response['SecretString'])
            else:
                secret = response['SecretBinary']

            self._cache[secret_name] = secret
            logger.info(f"Retrieved secret: {secret_name}")
            return secret

        except ImportError:
            logger.warning("boto3 not installed, cannot use AWS Secrets Manager")
            return {}
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

    def clear_cache(self):
        """Clear cached secrets (e.g., after key rotation)."""
        self._cache.clear()
        logger.info("Secrets cache cleared")


class ConfigLoader:
    """Loads and validates application configuration."""

    REQUIRED_KEYS = {
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'TOGETHER_API_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'STRIPE_API_KEY',
        'STRIPE_WEBHOOK_KEY',
    }

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize config loader.

        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file
        self._load_env_file()

    def _load_env_file(self):
        """Load environment variables from .env file if provided."""
        if self.env_file and os.path.exists(self.env_file):
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
            logger.debug(f"Loaded environment from {self.env_file}")

    def _get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with logging."""
        value = os.getenv(key, default)
        if value and key not in ['JWT_ALGORITHM', 'API_VERSION']:
            logger.debug(f"Loaded config: {key}")
        return value

    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Parse boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    def _get_int(self, key: str, default: int) -> int:
        """Parse integer environment variable."""
        try:
            return int(os.getenv(key, default))
        except ValueError:
            logger.warning(f"Invalid integer for {key}, using default: {default}")
            return default

    def _get_list(self, key: str, default: Optional[list] = None) -> list:
        """Parse comma-separated list from environment."""
        value = os.getenv(key)
        if not value:
            return default or []
        return [item.strip() for item in value.split(',')]

    def load(self) -> AppConfig:
        """
        Load and validate application configuration.

        Returns:
            AppConfig object

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        environment = self._get_env('ENVIRONMENT', 'development')

        aws_config = AWSConfig(
            access_key_id=self._get_env('AWS_ACCESS_KEY_ID'),
            secret_access_key=self._get_env('AWS_SECRET_ACCESS_KEY'),
            region=self._get_env('AWS_REGION', 'us-east-1'),
            secrets_manager_enabled=self._get_bool('AWS_SECRETS_MANAGER_ENABLED'),
            secrets_manager_region=self._get_env('AWS_SECRETS_MANAGER_REGION', 'us-east-1'),
            secrets_manager_secret_name=self._get_env('AWS_SECRETS_MANAGER_SECRET_NAME', 'aimodels/api/keys'),
            secrets_manager_secret_version_id=self._get_env('AWS_SECRETS_MANAGER_SECRET_VERSION_ID'),
        )

        secrets_manager = SecretsManager(aws_config)
        secrets = secrets_manager.get_secret(aws_config.secrets_manager_secret_name)

        def get_secret(key: str, env_var: Optional[str] = None) -> str:
            """Get secret from Secrets Manager or environment."""
            env_var = env_var or key.lower()
            if secrets and env_var in secrets:
                return secrets[env_var]
            return self._get_env(key) or self._get_env(key.upper())

        self._validate_required_keys(secrets, environment)

        openai_key = get_secret('OPENAI_API_KEY')
        anthropic_key = get_secret('ANTHROPIC_API_KEY')
        together_key = get_secret('TOGETHER_API_KEY')

        if not all([openai_key, anthropic_key, together_key]):
            raise ValueError("Missing required LLM provider keys")

        config = AppConfig(
            environment=environment,
            log_level=self._get_env('LOG_LEVEL', 'INFO'),
            api_port=self._get_int('API_PORT', 8000),
            api_version=self._get_env('API_VERSION', 'v1'),
            allowed_origins=self._get_list('ALLOWED_ORIGINS', ['http://localhost:3000']),
            debug=self._get_bool('DEBUG'),
            reload=self._get_bool('RELOAD'),
            verbose=self._get_bool('VERBOSE'),

            database=DatabaseConfig(
                url=get_secret('DATABASE_URL'),
                pool_size=self._get_int('DATABASE_POOL_SIZE', 20),
                pool_recycle_seconds=self._get_int('DATABASE_POOL_RECYCLE_SECONDS', 3600),
                echo=self._get_bool('DATABASE_ECHO'),
            ),

            redis=RedisConfig(
                url=get_secret('REDIS_URL'),
                decode_responses=self._get_bool('REDIS_DECODE_RESPONSES', True),
                socket_timeout=self._get_int('REDIS_SOCKET_TIMEOUT', 5),
                socket_connect_timeout=self._get_int('REDIS_SOCKET_CONNECT_TIMEOUT', 5),
            ),

            stripe=StripeConfig(
                api_key=get_secret('STRIPE_API_KEY'),
                webhook_key=get_secret('STRIPE_WEBHOOK_KEY'),
                api_version=self._get_env('STRIPE_API_VERSION', '2023-10-16'),
            ),

            llm_providers=LLMProvidersConfig(
                openai_api_key=openai_key,
                anthropic_api_key=anthropic_key,
                together_api_key=together_key,
            ),

            security=SecurityConfig(
                jwt_secret_key=self._get_env('JWT_SECRET_KEY') or self._generate_jwt_secret(),
                jwt_algorithm=self._get_env('JWT_ALGORITHM', 'HS256'),
                jwt_expiration_hours=self._get_int('JWT_EXPIRATION_HOURS', 24),
                rate_limit_requests_per_minute=self._get_int('RATE_LIMIT_REQUESTS_PER_MINUTE', 60),
                rate_limit_requests_per_hour=self._get_int('RATE_LIMIT_REQUESTS_PER_HOUR', 1000),
            ),

            aws=aws_config,

            observability=ObservabilityConfig(
                sentry_dsn=self._get_env('SENTRY_DSN'),
                posthog_api_key=self._get_env('POSTHOG_API_KEY'),
                posthog_api_host=self._get_env('POSTHOG_API_HOST', 'https://us.posthog.com'),
                cloudwatch_log_group=self._get_env('CLOUDWATCH_LOG_GROUP', '/aimodels/api'),
                cloudwatch_enabled=self._get_bool('CLOUDWATCH_ENABLED'),
            ),
        )

        if environment == 'production' and config.debug:
            raise ValueError("DEBUG mode must be disabled in production")

        logger.info(f"Configuration loaded for environment: {environment}")
        return config

    def _validate_required_keys(self, secrets: Dict, environment: str):
        """
        Validate that all required keys are present.

        Args:
            secrets: Secrets from Secrets Manager
            environment: Current environment

        Raises:
            ValueError: If required keys are missing
        """
        missing_keys = []
        for key in self.REQUIRED_KEYS:
            env_value = os.getenv(key)
            secret_value = secrets.get(key.lower()) if secrets else None

            if not env_value and not secret_value:
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(
                f"Missing required configuration keys: {', '.join(missing_keys)}. "
                f"Set them in .env or AWS Secrets Manager."
            )

    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret if not provided."""
        if os.getenv('ENVIRONMENT') == 'production':
            raise ValueError("JWT_SECRET_KEY must be set in production")

        import secrets
        secret = secrets.token_urlsafe(32)
        logger.warning("Generated temporary JWT secret - use a persistent value in production")
        return secret


@lru_cache(maxsize=1)
def get_config(env_file: Optional[str] = None) -> AppConfig:
    """
    Get singleton application configuration.

    Args:
        env_file: Path to .env file

    Returns:
        AppConfig object
    """
    loader = ConfigLoader(env_file)
    return loader.load()
