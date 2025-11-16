import subprocess
import sys
import os
from pathlib import Path

from bench.constants import DESIGNER_PATH, CONFIG_LOG_PATH

# Windows-specific flags for hiding windows
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = 0  # SW_HIDE
else:
    CREATE_NO_WINDOW = 0
    STARTUPINFO = None

BENCH_PATH = str(Path(__file__).parent.parent)

opener_path = f"{BENCH_PATH}/SampleOpener.epf"


class OneCEngine:

    def __init__(self, database_path: str, user_name: str = "Admin"):
        self.user_name = user_name
        self.database_path = database_path
        # Validate paths
        if not os.path.exists(DESIGNER_PATH):
            raise ValueError(f"Error: 1C Designer not found at {DESIGNER_PATH}")

        if not os.path.exists(database_path):
            raise ValueError(f"Error: Database not found at {database_path}")

    def _build_command(self, mode: str, extra_args: list[str], flags: list[str] = None) -> str:
        """
        Build command string for 1C Designer/Enterprise execution.
        Args:
            mode: 'CONFIG' or 'ENTERPRISE'
            extra_args: list of additional arguments (e.g. ['/LoadExternalDataProcessorOrReportFromFiles', ...])
            flags: list of flags (e.g. ['/DisableStartupDialogs', ...])
        Returns:
            str: command string
        """
        if flags is None:
            flags = []
        base_args = [
            f'"{DESIGNER_PATH}"',
            mode,
            f'/F "{self.database_path}"',
            f'/N {self.user_name}'
        ]
        cmd = ' '.join(base_args + extra_args + flags)
        return cmd

    def update_processing(self, processing_path, processing_storage_dir):

        processing_storage_root = Path(processing_storage_dir) / "SampleProcessor.xml"
        if not os.path.exists(processing_storage_root):
            raise AttributeError(f"Error: Processing files directory not found at {processing_storage_dir}")

        extra_args = [f'/LoadExternalDataProcessorOrReportFromFiles "{processing_storage_root}" "{processing_path}"']
        flags = ['/DisableStartupDialogs', '/DisableStartupMessages']
        cmd_str = self._build_command('CONFIG', extra_args, flags)
        # print()
        # print(cmd_str)
        try:
            # Execute the command with hidden window
            result = subprocess.run(
                cmd_str,
                shell=True,
                timeout=20,
                creationflags=CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                startupinfo=STARTUPINFO if sys.platform == 'win32' else None
            )

            # Check result
            if result.returncode == 0:
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

    def store_processing(self, processing_path: str | Path, target_dir: str | Path):

        if not os.path.exists(processing_path):
            raise AttributeError(f"Processing not found at {processing_path}")

        extra_args = [f'/DumpExternalDataProcessorOrReportToFiles "{target_dir}" "{processing_path}"']
        flags = ['/DisableStartupDialogs', '/DisableStartupMessages']
        cmd_str = self._build_command('CONFIG', extra_args, flags)
        # print()
        # print(cmd_str)
        try:
            # Execute the command with hidden window
            result = subprocess.run(
                cmd_str,
                shell=True,
                timeout=20,
                creationflags=CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                startupinfo=STARTUPINFO if sys.platform == 'win32' else None
            )

            # Check result
            if result.returncode == 0:
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

    def run_processing(self, processing_path: str | Path):

        processing_basename = Path(processing_path).name
        extra_args = [f'/Execute "{opener_path}"', f'/C"{processing_basename}"']
        flags = ['/DisableStartupMessages', '/DisableStartupDialogs']
        cmd_str = self._build_command('ENTERPRISE', extra_args, flags)
        # print()
        # print(cmd_str)
        try:
            # Execute the command with hidden window
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                startupinfo=STARTUPINFO if sys.platform == 'win32' else None
            )

            # Check result
            if result.returncode == 0:
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
