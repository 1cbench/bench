from pathlib import Path

import pandas as pd

from tqdm import tqdm

from bench.constants import PROCESSING_PATH, DATABASE_PATH, TASK_LOG_PATH
from bench.one_c_runner import OneCEngine


class BenchmarkRunner:

    def __init__(self):
        self.engine = OneCEngine(DATABASE_PATH)

    def run_sample(self, sample: dict) -> dict:
        object_module_path = Path(PROCESSING_PATH) / "Ext" / "ObjectModule.bsl"
        original_module_path = "data/ObjectModule.bsl"
        with open(original_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        existing_code = "\n".join(lines)

        result_code = (
            f"{existing_code}\n"
            f"{sample['run_context']}\n\n"
            f"{sample['code']}\n"
            f"{sample['validation_code']}"
        )

        with open(object_module_path, "w", encoding="utf-8") as f:
            f.write(result_code)

        self.engine.update_processing()
        self.engine.run_processing()
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

        for i, row in tqdm(df.iterrows(), total=len(df)):
            # if i != 8:
            #     continue

            sample = {
                "code": row[sample_field_name],
                "validation_code": row["validation"],
                "run_context": row["run_context"],
            }
            result = self.run_sample(sample)

            # Update counters based on result
            if result["compiled"]:
                compiled_count += 1
            if result["success"]:
                success_count += 1

        # Calculate rates
        compile_rate = compiled_count / total_samples if total_samples > 0 else 0
        success_rate = success_count / total_samples if total_samples > 0 else 0

        stats = {
            "number_of_samples": total_samples,
            "success_rate": success_rate,
            "compile_rate": compile_rate,
        }

        print(f"\nFinal Statistics:")
        print(f"Total samples: {stats['number_of_samples']}")
        print(f"Compile rate: {stats['compile_rate']:.2%}")
        print(f"Success rate: {stats['success_rate']:.2%}")

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

