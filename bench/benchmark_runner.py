import json
import os
import re
import shutil
import stat
import time
from pathlib import Path

import pandas as pd

from tqdm import tqdm

from bench.constants import PROCESSING_STORAGE_PATH, TASKS_PATH
from bench.mcp_runner import McpRunner
from bench.models import TaskModel
from bench.one_c_parser import OneCParser
from bench.v8_packer import V8Packer

MCP_URL = os.getenv("MCP_URL", "http://localhost:6003/mcp")

# Some bench EPFs (e.g. task_012) declare `Функция ЗапуститьРешение()` without
# Экспорт because the original SampleOpener flow invoked the exported wrapper
# ЗапуститьРешениеОбертка which called it internally. The MCP-based runner
# invokes ЗапуститьРешение directly from outside, so the entry point must be
# Экспорт-visible. Force it on after the LLM patch.
_ENTRY_POINT_EXPORT_RE = re.compile(
    r"(Функция\s+ЗапуститьРешение\s*\([^)]*\))(?!\s*Экспорт)",
    flags=re.IGNORECASE,
)


def _ensure_entry_point_exported(module_text: str) -> str:
    return _ENTRY_POINT_EXPORT_RE.sub(r"\1 Экспорт", module_text, count=1)


def _rmtree_force(path: Path) -> None:
    """Remove a directory tree on Windows, handling read-only files and brief locks."""
    def on_error(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except FileNotFoundError:
            pass

    last_exc: Exception | None = None
    for _ in range(3):
        try:
            shutil.rmtree(path, onerror=on_error)
            return
        except Exception as e:
            last_exc = e
            time.sleep(0.2)
    if last_exc is not None:
        raise last_exc


def _clear_dir(path: Path) -> None:
    """Empty a directory's contents while keeping the directory itself.

    On Windows, removing the directory node itself can fail with WinError 32
    when Explorer or another process has it open — clearing the contents
    avoids that and is enough for our purpose (re-unpacking into the dir).
    """
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            _rmtree_force(child)
        else:
            try:
                child.chmod(stat.S_IWRITE)
            except OSError:
                pass
            try:
                child.unlink()
            except FileNotFoundError:
                pass


class BenchmarkRunner:

    def __init__(self, mcp_url: str = MCP_URL):
        self.packer = V8Packer()
        self.runner = McpRunner(url=mcp_url)
        self.parser = OneCParser()

    @staticmethod
    def _detect_processing_name(processing_storage_dir: Path) -> str:
        xml_files = [
            f for f in Path(processing_storage_dir).iterdir()
            if f.suffix == ".xml" and f.is_file()
        ]
        if len(xml_files) != 1:
            raise AttributeError(
                f"Expected exactly 1 .xml file in {processing_storage_dir}, "
                f"found {len(xml_files)}: {xml_files}"
            )
        return xml_files[0].stem

    def prepare_processing_client(self, sample: TaskModel, processing_storage_dir: Path) -> None:
        processing_name = self._detect_processing_name(processing_storage_dir)
        object_module_path = (
            processing_storage_dir /
            processing_name /
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

    def prepare_processing_server(self, sample: TaskModel, processing_storage_dir: Path) -> None:
        processing_name = self._detect_processing_name(processing_storage_dir)
        object_module_path = (
            processing_storage_dir /
            processing_name /
            "Ext" /
            "ObjectModule.bsl"
        )

        with open(object_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            module_code = "\n".join(lines)

        result_code = self.parser.patch_function(module_code, sample.func_name, sample.code)
        result_code = _ensure_entry_point_exported(result_code)

        with open(object_module_path, "w", encoding="utf-8") as f:
            f.write(result_code)

    def run_sample(self, sample: TaskModel, dry_run: bool) -> dict:
        processing_storage_dir = Path(PROCESSING_STORAGE_PATH) / sample.task_id
        source_processing_path = Path(TASKS_PATH) / f"{sample.task_id}.epf"
        patched_processing_path = Path(TASKS_PATH) / f"{sample.task_id}_patched.epf"

        if dry_run:
            processing_to_run_path = source_processing_path
        else:
            # V8Packer's clone-and-swap pack path only rewrites the ObjectModule
            # entry; form-module patching is not supported.
            if sample.env == "client":
                raise NotImplementedError(
                    "client-side patching not supported by V8Packer pack path"
                )

            # Clean the target dir so the unpacked processing starts fresh
            os.makedirs(processing_storage_dir, exist_ok=True)
            _clear_dir(processing_storage_dir)

            self.packer.unpack_epf(source_processing_path, processing_storage_dir)
            self.prepare_processing_server(sample, processing_storage_dir)
            self.packer.pack_epf(
                source_processing_path,
                processing_storage_dir,
                patched_processing_path,
            )
            processing_to_run_path = patched_processing_path

        return self.runner.run_epf(str(processing_to_run_path))

    def run(
        self,
        filename: str,
        dry_run: bool = False,
        output_path: str | None = None,
    ) -> dict:
        sample_field_name = "gt_solution" if dry_run else "output"
        df = pd.read_csv(filename)

        # Initialize counters
        total_samples = len(df)
        compiled_count = 0
        success_count = 0
        compile_succeeded_ids = []
        compile_failed_ids = []
        success_succeeded_ids = []
        success_failed_ids = []
        parse_errors = []
        task_results = []

        def build_stats() -> dict:
            return {
                "number_of_samples": total_samples,
                "success_rate": success_count / total_samples if total_samples > 0 else 0,
                "compile_rate": compiled_count / total_samples if total_samples > 0 else 0,
                "compile_succeeded_ids": compile_succeeded_ids,
                "compile_failed_ids": compile_failed_ids,
                "success_succeeded_ids": success_succeeded_ids,
                "success_failed_ids": success_failed_ids,
                "parse_errors": parse_errors,
                "task_results": task_results,
            }

        def save_report() -> None:
            if not output_path:
                return
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(build_stats(), f, indent=2, ensure_ascii=False)

        for i, row in tqdm(df.iterrows(), total=len(df)):
            task_id = row["task_id"]

            # if task_id != "task_026":
            #     continue
            code = None
            func_name = None
            if not dry_run:
                code = row[sample_field_name]
                code = self.parser.clean_code(code)  # Remove invisible characters
                func_name = self.parser.extract_func_name(code)

                if not func_name:
                    err_msg = "Function name could not be extracted from code"
                    parse_errors.append({
                        "row": i,
                        "task_id": task_id,
                        "error": err_msg,
                    })
                    compile_failed_ids.append(task_id)
                    success_failed_ids.append(task_id)
                    task_results.append({
                        "task_id": task_id,
                        "status": "error",
                        "error": err_msg,
                    })
                    save_report()
                    continue

            try:
                sample = TaskModel(
                    code=code,
                    task_id=task_id,
                    env=row["env"],
                    func_name=func_name,
                )
                result = self.run_sample(sample, dry_run)
            except Exception as e:
                err_msg = str(e)
                parse_errors.append({
                    "row": i,
                    "task_id": task_id,
                    "error": err_msg,
                })
                compile_failed_ids.append(task_id)
                success_failed_ids.append(task_id)
                task_results.append({
                    "task_id": task_id,
                    "status": "error",
                    "error": err_msg,
                })
                save_report()
                continue

            # Update counters based on result
            if result["compiled"]:
                compiled_count += 1
                compile_succeeded_ids.append(task_id)
            else:
                compile_failed_ids.append(task_id)
            if result["success"]:
                success_count += 1
                success_succeeded_ids.append(task_id)
            else:
                success_failed_ids.append(task_id)

            if result["success"]:
                status, err_text = "success", ""
            elif result["compiled"]:
                status, err_text = "compiled", ""
            else:
                status, err_text = "error", result.get("error", "")
            task_results.append({
                "task_id": task_id,
                "status": status,
                "error": err_text,
            })
            save_report()

        return build_stats()
