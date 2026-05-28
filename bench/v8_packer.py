"""
V8Packer — replacement for OneCEngine.store_processing / update_processing.

Instead of invoking 1C Designer via subprocess, we use the pure-Python
v8pack utility (bench/v8pack.py) to:
  - unpack an EPF into the same folder layout the bench expects
    (so the existing BenchmarkRunner.prepare_processing_* code keeps working);
  - rebuild a patched EPF by cloning the original container and swapping
    only the ObjectModule .0 entry with the freshly patched BSL.

All bench tasks use env="server", so only ObjectModule.bsl needs patching;
the form module / template / metadata are reused from the original EPF.
"""

import contextlib
import io
from pathlib import Path

from bench import v8pack


class V8Packer:

    def unpack_epf(self, epf_path: str | Path, target_dir: str | Path) -> None:
        epf_path = str(epf_path)
        target_dir = str(target_dir)
        # v8pack.unpack_epf prints a line per extracted file. Silence it so
        # the bench tqdm progress bar stays clean — we don't lose anything
        # since these aren't error messages.
        with contextlib.redirect_stdout(io.StringIO()):
            v8pack.unpack_epf(epf_path, target_dir)

    def pack_epf(
        self,
        source_epf_path: str | Path,
        processing_storage_dir: str | Path,
        output_epf_path: str | Path,
    ) -> None:
        source_epf_path = Path(source_epf_path)
        processing_storage_dir = Path(processing_storage_dir)
        output_epf_path = Path(output_epf_path)

        processing_name = self._detect_processing_name(processing_storage_dir)
        module_path = (
            processing_storage_dir / processing_name / "Ext" / "ObjectModule.bsl"
        )
        new_module_bsl = module_path.read_bytes()

        # Clone the original EPF and replace only the ObjectModule .0 entry.
        ref_files = dict(
            v8pack.read_container(source_epf_path.read_bytes())
        )

        # The ObjectModule lives in the orphan ".0" entry: a key ending in ".0"
        # whose base key isn't a separate container entry (forms/templates have
        # both a metadata entry and a ".0" data entry).
        module_key = None
        for key in ref_files:
            if key.endswith(".0") and key != "copyinfo" and key[:-2] not in ref_files:
                module_key = key
                break
        if module_key is None:
            raise RuntimeError(
                f"Could not find ObjectModule key in EPF {source_epf_path}"
            )

        ref_files[module_key] = v8pack.make_module_container(new_module_bsl)
        epf_bytes = v8pack.write_container(list(ref_files.items()), compress=True)
        output_epf_path.write_bytes(epf_bytes)

    @staticmethod
    def _detect_processing_name(processing_storage_dir: Path) -> str:
        xml_files = [
            f for f in processing_storage_dir.iterdir()
            if f.suffix == ".xml" and f.is_file()
        ]
        if len(xml_files) != 1:
            raise AttributeError(
                f"Expected exactly 1 .xml file in {processing_storage_dir}, "
                f"found {len(xml_files)}: {xml_files}"
            )
        return xml_files[0].stem
