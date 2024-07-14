import pathlib
import os
from logging.config import dictConfig
from dotenv import load_dotenv

# Base directory and important subdirectories
BASE_DIR = pathlib.Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
COMMANDS_DIR = BASE_DIR / "commands"
DATA_DIR = BASE_DIR / "data"

# Ensure necessary directories exist
for directory in [LOGS_DIR, COMMANDS_DIR, DATA_DIR]:
    directory.mkdir(exist_ok=True)

# Load environment variables
load_dotenv()

# Bot Configuration
DISCORD_API_SECRET = os.getenv("DISCORD_API_SECRET")
BASE_OWNER_ID = int(os.getenv("BASE_OWNER_ID", 0))

# Database Configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))  # Default MySQL port is 3306
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
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "infos.log",
            "mode": "a",
            "formatter": "normal",
            "maxBytes": 50 * 1024 * 1024,  # 50 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "bot": {"handlers": ["file"], "level": "DEBUG", "propagate": True},
        "discord": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "__main__": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "database": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "command": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "helpers": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Apply logging configuration
dictConfig(LOGGING_CONFIG)

# Database URL (for SQLAlchemy)
DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Bot Version
BOT_NAME = "Tarkov Cheater Tracker"
BOT_VERSION = "1.0"
