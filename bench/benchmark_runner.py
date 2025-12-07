import os
from pathlib import Path

import pandas as pd

from tqdm import tqdm

from bench.constants import DATABASE_PATH, TASK_LOG_PATH, PROCESSING_STORAGE_PATH, TASKS_PATH, PROCESSING_NAME
from bench.one_c_parser import OneCParser
from bench.one_c_runner import OneCEngine
from bench.models import TaskModel


class BenchmarkRunner:

    def __init__(self):
        self.engine = OneCEngine(DATABASE_PATH)
        self.parser = OneCParser()

    def prepare_processing_client(self, sample: TaskModel) -> None:
        object_module_path = (
            Path(PROCESSING_STORAGE_PATH) /
            sample.task_id /
            PROCESSING_NAME /
            "Forms" /
            "Форма" /
            "Ext" /
            "Form" /
            "Module.bsl"
        )

        with open(object_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            module_code = "\n".join(lines)

        result_code = self.parser.patch_function(module_code, sample.func_name, sample.code)

        with open(object_module_path, "w", encoding="utf-8") as f:
            f.write(result_code)

    def prepare_processing_server(self, sample: TaskModel) -> None:
        object_module_path = (
            Path(PROCESSING_STORAGE_PATH) /
            sample.task_id /
            PROCESSING_NAME /
            "Ext" /
            "ObjectModule.bsl"
        )

        with open(object_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            module_code = "\n".join(lines)

        result_code = self.parser.patch_function(module_code, sample.func_name, sample.code)

        with open(object_module_path, "w", encoding="utf-8") as f:
            f.write(result_code)

    def run_sample(self, sample: TaskModel, dry_run: bool) -> dict:
        processing_storage_dir = Path(PROCESSING_STORAGE_PATH) / sample.task_id
        source_processing_path = Path(TASKS_PATH) / f"{sample.task_id}.epf"
        patched_processing_path = Path(TASKS_PATH) / f"{sample.task_id}_patched.epf"
        os.makedirs(processing_storage_dir, exist_ok=True)

        # Delete log file if exists
        if os.path.exists(TASK_LOG_PATH):
            os.remove(TASK_LOG_PATH)

        if dry_run:
            processing_to_run_path = source_processing_path
        else:
            self.engine.store_processing(source_processing_path, processing_storage_dir)

            if sample.env == "client":
                self.prepare_processing_client(sample)
            else:
                self.prepare_processing_server(sample)

            self.engine.update_processing(patched_processing_path, processing_storage_dir)
            processing_to_run_path = patched_processing_path

        self.engine.run_processing(processing_path=processing_to_run_path)

        return self.parse_logs()

    def run(
        self,
        filename: str,
        dry_run: bool = False
    ) -> dict:
        sample_field_name = "gt_solution" if dry_run else "output"
        df = pd.read_csv(filename)

        # Initialize counters
        total_samples = len(df)
        compiled_count = 0
        success_count = 0
        compile_failed_ids = []
        success_failed_ids = []

        for i, row in tqdm(df.iterrows(), total=len(df)):

            code = None
            func_name = None
            if not dry_run:
                code = row[sample_field_name]
                code = self.parser.clean_code(code)  # Remove invisible characters
                func_name = self.parser.extract_func_name(code)

                if not func_name:
                    raise AttributeError(f"Function name could not be extracted from code in row {i}")

            sample = TaskModel(
                code=code,
                task_id=row["task_id"],
                env=row["env"],
                func_name=func_name,
            )
            result = self.run_sample(sample, dry_run)

            # Update counters based on result
            task_id = row["task_id"]
            if result["compiled"]:
                compiled_count += 1
            else:
                compile_failed_ids.append(task_id)
            if result["success"]:
                success_count += 1
            else:
                success_failed_ids.append(task_id)

        # Calculate rates
        compile_rate = compiled_count / total_samples if total_samples > 0 else 0
        success_rate = success_count / total_samples if total_samples > 0 else 0

        stats = {
            "number_of_samples": total_samples,
            "success_rate": success_rate,
            "compile_rate": compile_rate,
            "compile_failed_ids": compile_failed_ids,
            "success_failed_ids": success_failed_ids,
        }

        return stats

    def parse_logs(self) -> dict:
        """Parse the 1C benchmark log file and return compilation and execution status."""
        error_prefix = "Error:"
        try:
            with open(TASK_LOG_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Check if compilation failed (log starts with "Error")
            compiled = error_prefix not in content

            # Check for success (Result: true)
            success = "Result: true" in content

            # Extract error message if present
            error = ""
            if error_prefix in content:
                # Extract the error message (everything after "Error: ")
                lines = content.split("\n")
                if lines and error_prefix in lines[0]:
                    error = (
                        lines[0][len(error_prefix) + 1 :].strip()
                    )  # Remove "Error: " prefix

            return {
                "compiled": compiled,
                "success": success,
                "error": error,
            }

        except FileNotFoundError:
            return {
                "compiled": False,
                "success": False,
                "error": "Log file not found",
            }
        except Exception as e:
            print(f"Error reading log file: {str(e)}")
            return {
                "compiled": False,
                "success": False,
                "error": f"Error reading log file: {str(e)}",
            }
