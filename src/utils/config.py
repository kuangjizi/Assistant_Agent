# src/utils/config.py
import yaml
import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Config:
    # Database
    database_url: str

    # OpenAI
    openai_api_key: str

    # Email
    smtp_server: str
    smtp_port: int
    email_username: str
    email_password: str
    recipient_emails: List[str]

    # Vector Store
    vector_store_path: str

    # Web Scraping
    user_agent: str
    request_delay: float

    def __init__(self, config_path: str = "config/config.yaml"):
        self.load_config(config_path)

    def load_config(self, config_path: str):
        # Load from environment variables first
        self.database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ai_assistant")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        # Load from YAML file
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                config_data = yaml.safe_load(file)

                # Override with file values if present
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

        # Set defaults for missing values
        self._set_defaults()

    def _set_defaults(self):
        if not hasattr(self, 'smtp_server'):
            self.smtp_server = "smtp.gmail.com"
        if not hasattr(self, 'smtp_port'):
            self.smtp_port = 587
        if not hasattr(self, 'vector_store_path'):
            self.vector_store_path = "./data/vector_store"
        if not hasattr(self, 'user_agent'):
            self.user_agent = "AI-Assistant-Agent/1.0"
        if not hasattr(self, 'request_delay'):
            self.request_delay = 1.0
