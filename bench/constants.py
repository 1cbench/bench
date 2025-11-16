import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

ROOT_DIR = Path(__file__).parent.parent

# Load constants from environment variables
DESIGNER_PATH = os.getenv("DESIGNER_PATH")
DATABASE_PATH = os.getenv("DATABASE_PATH")
CONFIG_STORAGE_PATH = os.getenv("CONFIG_STORAGE_PATH")

# Derived paths (can be overridden by environment variables)
PROCESSING_STORAGE_PATH = os.getenv("PROCESSING_STORAGE_PATH", f"{ROOT_DIR}/processing_storage/")
TASK_LOG_PATH = os.getenv("TASK_LOG_PATH", f"{ROOT_DIR}/tasks/logs/benchmark_1c.log")
CONFIG_LOG_PATH = os.getenv("CONFIG_LOG_PATH", f"{ROOT_DIR}/data/logs/")
TASKS_PATH = os.getenv("TASKS_PATH", f"{ROOT_DIR}/tasks/")

# Processing configuration
PROCESSING_NAME = os.getenv("PROCESSING_NAME", "SampleProcessor")
USER_NAME = os.getenv("USER_NAME", "Admin")
