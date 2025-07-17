# src/utils/config_manager.py
import yaml
import os
import re
from pathlib import Path
from typing import Any, Dict
import logging

class ConfigManager:
    """Configuration manager that loads settings from YAML and environment variables"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)

        self.config_data = self._load_config()
        self.logger.info(f"Configuration loaded from {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Substitute environment variables
            content = self._substitute_env_vars(content)

            # Parse YAML
            config = yaml.safe_load(content)

            return config or {}

        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise # Re-raise the FileNotFoundError to propagate the exception
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise

    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in format ${VAR} or ${VAR:default}"""

        def replace_var(match):
            var_expr = match.group(1)

            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
            else:
                var_name, default_value = var_expr, ''

            return os.getenv(var_name, default_value)

        # Pattern to match ${VAR} or ${VAR:default}
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, content)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Dot-separated path (e.g., 'database.url')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config_data

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation

        Args:
            key_path: Dot-separated path (e.g., 'database.url')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config_data

        # Navigate to parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section

        Args:
            section: Section name (e.g., 'database')

        Returns:
            Dictionary with section configuration
        """
        return self.get(section, {})

    def reload(self) -> None:
        """Reload configuration from file"""
        self.config_data = self._load_config()
        self.logger.info("Configuration reloaded")

    def validate_required_settings(self) -> bool:
        """
        Validate that required settings are present

        Returns:
            True if all required settings are present
        """
        required_settings = [
            'openai.api_key',
            'google.api_key',
            'database.url',
            'email.username',
            'email.password'
        ]

        missing_settings = []

        for setting in required_settings:
            value = self.get(setting)
            if not value or value == "your-api-key-here" or value == "your-email@gmail.com":
                missing_settings.append(setting)

        if missing_settings:
            self.logger.error(f"Missing required configuration settings: {missing_settings}")
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self.config_data.copy()

    # Convenience properties for commonly used settings
    @property
    def database_url(self) -> str:
        return self.get('database.url')

    @property
    def openai_model_config(self) -> Dict[str, Any]:
        return self.get_section('openai')

    @property
    def google_model_config(self) -> Dict[str, Any]:
        return self.get_section('google')

    @property
    def email_config(self) -> Dict[str, Any]:
        return self.get_section('email')

    @property
    def vector_store_config(self) -> Dict[str, Any]:
        return self.get_section('vector_store')

    @property
    def scraping_config(self) -> Dict[str, Any]:
        return self.get_section('scraping')

    @property
    def is_debug(self) -> bool:
        return self.get('app.debug', False)


# Global configuration instance (singleton)
_config_instance = None

def get_config(config_path: str = 'config/config.yaml') -> ConfigManager:
    """Get global configuration instance"""
    global _config_instance

    if _config_instance is None:
        _config_instance = ConfigManager(config_path)

    return _config_instance

def reload_config() -> None:
    """Reload global configuration"""
    global _config_instance
    if _config_instance:
        _config_instance.reload()
