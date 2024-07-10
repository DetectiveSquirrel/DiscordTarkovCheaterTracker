import pathlib
import os
from logging.config import dictConfig
from dotenv import load_dotenv

# Ensure the logs directory exists before configuring logging
BASE_DIR = pathlib.Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
CMDS_DIR = BASE_DIR / "cmds"
COGS_DIR = BASE_DIR / "cogs"
DATA_DIR = BASE_DIR / "data"

# Parse env
load_dotenv()

# Bot Token
DISCORD_API_SECRET = os.getenv("DISCORD_API_SECRET")

# Base Config
BASE_OWNER_ID = int(os.getenv("BASE_OWNER_ID", 0))

# Database Config
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")  # Default MySQL port is 3306
DB_NAME = os.getenv("DB_NAME")

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "normal",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/infos.log",
            "mode": "a",
            "formatter": "normal",
            "maxBytes": 50 * 1024 * 1024,  # 50 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "bot": {"handlers": ["file"], "level": "INFO", "propagate": True},
        "discord": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "__main__": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "database": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

dictConfig(LOGGING_CONFIG)
