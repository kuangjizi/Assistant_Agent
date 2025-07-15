# tests/unit/test_config_manager.py
import pytest
import os
import sys
from pathlib import Path
import yaml
from unittest.mock import patch, mock_open

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.config_manager import ConfigManager, get_config

class TestConfigManager:

    def test_load_config_from_file(self, test_config_file, test_config_data):
        """Test loading configuration from YAML file"""
        config = ConfigManager(test_config_file)

        assert config.get('app.name') == test_config_data['app']['name']
        assert config.get('database.url') == test_config_data['database']['url']
        assert config.get('openai.api_key') == test_config_data['openai']['api_key']

    def test_get_with_dot_notation(self, test_config_file):
        """Test getting values with dot notation"""
        config = ConfigManager(test_config_file)

        assert config.get('app.name') == 'Test AI Assistant'
        assert config.get('database.pool_size') == 5
        assert config.get('nonexistent.key', 'default') == 'default'

    def test_get_section(self, test_config_file, test_config_data):
        """Test getting entire configuration sections"""
        config = ConfigManager(test_config_file)

        email_section = config.get_section('email')
        assert email_section == test_config_data['email']

        nonexistent_section = config.get_section('nonexistent')
        assert nonexistent_section == {}

    def test_set_value(self, test_config_file):
        """Test setting configuration values"""
        config = ConfigManager(test_config_file)

        config.set('app.new_setting', 'new_value')
        assert config.get('app.new_setting') == 'new_value'

        config.set('new_section.key', 'value')
        assert config.get('new_section.key') == 'value'

    def test_environment_variable_substitution(self, temp_dir):
        """Test environment variable substitution in config"""
        config_content = """
        database:
          url: "${TEST_DB_URL:sqlite:///:memory:}"
        api:
          key: "${TEST_API_KEY}"
        """

        config_path = Path(temp_dir) / "test_env_config.yaml"
        with open(config_path, 'w') as f:
            f.write(config_content)

        # Test with environment variable set
        with patch.dict(os.environ, {'TEST_DB_URL': 'postgresql://test', 'TEST_API_KEY': 'secret'}):
            config = ConfigManager(str(config_path))
            assert config.get('database.url') == 'postgresql://test'
            assert config.get('api.key') == 'secret'

        # Test with default value
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigManager(str(config_path))
            assert config.get('database.url') == 'sqlite:///:memory:'
            assert config.get('api.key') == ''

    def test_validate_required_settings(self, test_config_file):
        """Test validation of required settings"""
        config = ConfigManager(test_config_file)

        # Should pass with test config
        assert config.validate_required_settings() == True

        # Should fail with missing settings
        config.set('openai.api_key', '')
        assert config.validate_required_settings() == False

    def test_properties(self, test_config_file, test_config_data):
        """Test convenience properties"""
        config = ConfigManager(test_config_file)

        assert config.database_url == test_config_data['database']['url']
        assert config.openai_api_key == test_config_data['openai']['api_key']
        assert config.email_config == test_config_data['email']
        assert config.is_debug == True

    def test_file_not_found(self):
        """Test handling of missing config file"""
        with pytest.raises(FileNotFoundError):
            ConfigManager('nonexistent_config.yaml')

    def test_invalid_yaml(self, temp_dir):
        """Test handling of invalid YAML"""
        config_path = Path(temp_dir) / "invalid.yaml"
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            ConfigManager(str(config_path))

    def test_reload_config(self, test_config_file):
        """Test reloading configuration"""
        config = ConfigManager(test_config_file)
        original_name = config.get('app.name')

        # Modify the file
        with open(test_config_file, 'r') as f:
            data = yaml.safe_load(f)

        data['app']['name'] = 'Modified Name'

        with open(test_config_file, 'w') as f:
            yaml.dump(data, f)

        # Reload and check
        config.reload()
        assert config.get('app.name') == 'Modified Name'
        assert config.get('app.name') != original_name

class TestGlobalConfig:

    def test_get_config_singleton(self, test_config_file):
        """Test global configuration singleton"""
        config1 = get_config(test_config_file)
        config2 = get_config()

        assert config1 is config2
