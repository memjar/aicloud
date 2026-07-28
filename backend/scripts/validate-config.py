#!/usr/bin/env python3

"""
Configuration validation script.
Validates all required keys are present and accessible.

Usage:
    python scripts/validate-config.py [--env environment] [--aws-enabled]
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import ConfigLoader, ConfigValidator


class ConfigValidator:
    """Validates configuration is complete and correct."""

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks: Dict[str, bool] = {}

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print(f"\n{'='*60}")
        print(f"Configuration Validation - {self.environment.upper()}")
        print(f"{'='*60}\n")

        try:
            self.check_environment()
            self.check_env_file()
            self.check_required_keys()
            self.check_configuration_load()
            self.check_security_settings()
            self.check_aws_secrets()
        except Exception as e:
            self.errors.append(f"Validation failed: {e}")

        self.print_results()
        return len(self.errors) == 0

    def check_environment(self):
        """Check environment is valid."""
        print("1. Checking environment...")
        valid = self.environment in ('development', 'staging', 'production')
        self.checks['environment'] = valid

        if valid:
            self._success(f"Environment: {self.environment}")
        else:
            self._error(f"Invalid environment: {self.environment}")

    def check_env_file(self):
        """Check if environment file exists."""
        print("2. Checking .env file...")

        env_file = f".env.{self.environment}"
        path = Path(env_file)

        if path.exists():
            self._success(f"Found: {env_file}")
            self.checks['env_file'] = True
        else:
            self._warning(f"Not found: {env_file}")
            self.checks['env_file'] = False

    def check_required_keys(self):
        """Check all required keys are present."""
        print("3. Checking required keys...")

        required = {
            'OPENAI_API_KEY': False,
            'ANTHROPIC_API_KEY': False,
            'TOGETHER_API_KEY': False,
            'DATABASE_URL': False,
            'REDIS_URL': False,
            'STRIPE_API_KEY': False,
            'STRIPE_WEBHOOK_KEY': False,
        }

        for key in required:
            value = os.getenv(key)
            has_key = bool(value and value != 'set_via_aws_secrets_manager')
            required[key] = has_key

            if has_key:
                self._success(f"{key}: ✓ present")
            else:
                self._warning(f"{key}: missing (expected from AWS Secrets Manager or .env)")

        all_present = all(required.values())
        self.checks['required_keys'] = all_present

        if not all_present and self.environment == 'production':
            self._error("Production requires all keys to be set")

    def check_configuration_load(self):
        """Try to load actual configuration."""
        print("4. Loading configuration...")

        try:
            from src.config import get_config

            config = get_config(f".env.{self.environment}")
            self._success("Configuration loaded successfully")

            # Print configuration summary
            print(f"\n  Configuration Summary:")
            print(f"  ├─ Environment: {config.environment}")
            print(f"  ├─ Log Level: {config.log_level}")
            print(f"  ├─ API Port: {config.api_port}")
            print(f"  ├─ Debug: {config.debug}")
            print(f"  ├─ Database: {config.database.url[:40]}...")
            print(f"  ├─ Redis: {config.redis.url[:40]}...")
            print(f"  └─ Stripe: {'✓' if config.stripe.api_key else '✗'}")

            self.checks['config_load'] = True

        except ValueError as e:
            self._error(f"Configuration load failed: {e}")
            self.checks['config_load'] = False
        except Exception as e:
            self._error(f"Unexpected error: {e}")
            self.checks['config_load'] = False

    def check_security_settings(self):
        """Check security-related settings."""
        print("5. Checking security settings...")

        checks = []

        # Check debug in production
        if self.environment == 'production':
            debug = os.getenv('DEBUG', 'false').lower() == 'true'
            if not debug:
                self._success("Debug disabled in production")
                checks.append(True)
            else:
                self._error("DEBUG must be disabled in production")
                checks.append(False)

        # Check JWT secret
        jwt_secret = os.getenv('JWT_SECRET_KEY', '')
        if len(jwt_secret) >= 32:
            self._success("JWT secret is strong (>=32 chars)")
            checks.append(True)
        elif self.environment == 'production':
            self._error("JWT secret must be >=32 chars in production")
            checks.append(False)
        else:
            self._warning("JWT secret is short (consider increasing length)")
            checks.append(True)

        # Check allowed origins
        origins = os.getenv('ALLOWED_ORIGINS', '')
        if origins and 'http://' not in origins:
            self._success("All origins use HTTPS")
            checks.append(True)
        elif self.environment == 'production':
            self._error("Production must use HTTPS origins only")
            checks.append(False)
        else:
            self._warning("Development using HTTP (OK for local)")
            checks.append(True)

        self.checks['security'] = all(checks)

    def check_aws_secrets(self):
        """Check AWS Secrets Manager configuration if enabled."""
        print("6. Checking AWS Secrets Manager...")

        aws_enabled = os.getenv('AWS_SECRETS_MANAGER_ENABLED', 'false').lower() == 'true'

        if not aws_enabled:
            self._success("Secrets Manager disabled (using environment)")
            self.checks['aws_secrets'] = True
            return

        # Check AWS CLI
        try:
            import boto3
            self._success("boto3 installed")

            # Check credentials
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            account_id = identity['Account']
            arn = identity['Arn']
            self._success(f"AWS credentials valid (Account: {account_id})")

            # Check secrets
            region = os.getenv('AWS_SECRETS_MANAGER_REGION', 'us-east-1')
            secret_name = os.getenv('AWS_SECRETS_MANAGER_SECRET_NAME', 'aimodels/api/keys')

            secrets_client = boto3.client('secretsmanager', region_name=region)
            try:
                response = secrets_client.describe_secret(SecretId=secret_name)
                self._success(f"Secret found: {secret_name} (region: {region})")
                self.checks['aws_secrets'] = True
            except Exception as e:
                self._error(f"Secret not found: {secret_name} - {e}")
                self.checks['aws_secrets'] = False

        except ImportError:
            self._warning("boto3 not installed - cannot verify AWS Secrets Manager")
            self.checks['aws_secrets'] = False
        except Exception as e:
            self._error(f"AWS check failed: {e}")
            self.checks['aws_secrets'] = False

    def _success(self, message: str):
        """Print success message."""
        print(f"  ✓ {message}")

    def _warning(self, message: str):
        """Print warning message."""
        print(f"  ⚠ {message}")
        self.warnings.append(message)

    def _error(self, message: str):
        """Print error message."""
        print(f"  ✗ {message}")
        self.errors.append(message)

    def print_results(self):
        """Print validation summary."""
        print(f"\n{'='*60}")
        print("Validation Results")
        print(f"{'='*60}\n")

        # Checks summary
        print("Checks:")
        for check_name, result in self.checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}: {'PASS' if result else 'FAIL'}")

        # Warnings
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        # Errors
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ✗ {error}")

        # Overall result
        print(f"\n{'='*60}")
        if not self.errors:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration validation failed")
        print(f"{'='*60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate aimodels configuration")
    parser.add_argument(
        '--env',
        default='development',
        choices=['development', 'staging', 'production'],
        help='Environment to validate'
    )
    parser.add_argument(
        '--no-aws-check',
        action='store_true',
        help='Skip AWS Secrets Manager checks'
    )

    args = parser.parse_args()

    # Load environment
    env_file = f".env.{args.env}"
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)

    validator = ConfigValidator(args.env)
    success = validator.validate_all()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
