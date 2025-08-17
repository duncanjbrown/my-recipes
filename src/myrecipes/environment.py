import os
from .config import AppConfig
from dotenv import load_dotenv

load_dotenv()

config = AppConfig(environment=os.environ.get("ENVIRONMENT").lower())
