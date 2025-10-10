import subprocess
import sys
import os
from pathlib import Path

from bench.constants import DESIGNER_PATH, CONFIG_LOG_PATH

config_files_path = "c:/Work/projects/sberdevices/dev/1cbench/bench/SampleProcessor.xml"
processing_path = "c:/Work/projects/sberdevices/dev/1cbench/bench/SampleProcessor.epf"


class OneCEngine:

    def __init__(self, database_path: str, user_name: str = "Admin"):
        self.user_name = user_name
        self.database_path = database_path
        # Validate paths
        if not os.path.exists(DESIGNER_PATH):
            raise ValueError(f"Error: 1C Designer not found at {DESIGNER_PATH}")

        if not os.path.exists(database_path):
            raise ValueError(f"Error: Database not found at {database_path}")

    def update_processing(self):

        if not os.path.exists(config_files_path):
            print(f"Error: Configuration files directory not found at {config_files_path}")
            return False

        cmd_str = f'"{DESIGNER_PATH}" CONFIG /F "{self.database_path}" /N {self.user_name} /LoadExternalDataProcessorOrReportFromFiles"{config_files_path}"{processing_path}"'
        # print()
        # print(cmd_str)
        try:
            # Execute the command
            result = subprocess.run(
                cmd_str,
                shell=True,
                timeout=20  # 5 minute timeout
            )

            # Check result
            if result.returncode == 0:
                # print("✓ Configuration loaded successfully!")
                if result.stdout:
                    print("Output:", result.stdout)
            else:
                print(f"✗ Error loading configuration (exit code: {result.returncode})")
                if result.stderr:
                    print("Error output:", result.stderr)
                if result.stdout:
                    print("Standard output:", result.stdout)
                return False
        except subprocess.TimeoutExpired:
            print("✗ Error: Operation timed out after 5 minutes")
            return False

    def run_processing(self):

        cmd_str = f'"{DESIGNER_PATH}" ENTERPRISE /F "{self.database_path}" /N {self.user_name} /Execute "{processing_path}" /DisableStartupMessages'

        # print(cmd_str)
        try:
            # Execute the command
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120  # 5 minute timeout
            )

            # Check result
            if result.returncode == 0:
                # print("✓ Configuration loaded successfully!")
                if result.stdout:
                    print("Output:", result.stdout)
            else:
                print(f"✗ Error loading configuration (exit code: {result.returncode})")
                if result.stderr:
                    print("Error output:", result.stderr)
                if result.stdout:
                    print("Standard output:", result.stdout)
                return False
        except subprocess.TimeoutExpired:
            print("✗ Error: Operation timed out after 5 minutes")
            return False

