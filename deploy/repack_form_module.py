"""Swap the embedded Module.bsl of a single form inside an .epf.

The MCP_Toolkit.epf has multiple forms and templates that v8pack's
`pack`/`pack-simple` paths can't reproduce (those are hardcoded for a
single-form / single-template skeleton). For our use case we only need
to change one form's Module.bsl, so we read the existing .epf, locate
the form's embedded BSL string in the serialized form data, splice in
the new text, and rewrite the container.

Usage:
    python repack_form_module.py <in.epf> <form_name> <module.bsl> <out.epf>
"""
import sys

sys.path.insert(0, r"C:\Work\projects\sberdevices\dev\gc-mini-cli-pub")

from v8pack import (
    read_container,
    write_container,
    _content_text,
    _parse_string,
    _extract_metadata_fields,
    BOM_UTF8,
)


def repack(epf_in: str, form_name: str, new_module_path: str, epf_out: str) -> None:
    with open(epf_in, "rb") as f:
        raw = f.read()

    files = read_container(raw)
    files_dict = dict(files)

    info = _extract_metadata_fields(files_dict)

    form_uuid = next(
        (u for u, fi in info["forms"].items() if fi["name"] == form_name), None
    )
    if form_uuid is None:
        names = [fi["name"] for fi in info["forms"].values()]
        raise SystemExit(f"Form {form_name!r} not found. Available: {names}")

    form_key = f"{form_uuid}.0"
    form_bytes = files_dict[form_key]
    form_text = _content_text(form_bytes)

    # The embedded module is the largest top-level quoted string in the
    # serialized form data. Walking top-level strings is robust to whether
    # the module starts with `&НаКлиенте`, `//`, `Перем`, etc.
    best_start, best_end, best_len = -1, -1, -1
    pos = 0
    while pos < len(form_text):
        if form_text[pos] == '"':
            s, end = _parse_string(form_text, pos)
            if len(s) > best_len:
                best_start, best_end, best_len = pos, end, len(s)
            pos = end
        else:
            pos += 1
    if best_start == -1:
        raise SystemExit("No quoted strings found in form data")

    orig_module = form_text[best_start + 1 : best_end - 1]
    end_pos = best_end

    with open(new_module_path, "rb") as f:
        new_bsl_bytes = f.read()
    if new_bsl_bytes[:3] == BOM_UTF8:
        new_bsl_bytes = new_bsl_bytes[3:]
    new_text = new_bsl_bytes.decode("utf-8")

    # Match the line-ending convention of the original embedded module.
    use_crlf = "\r\n" in orig_module
    new_text = new_text.replace("\r\n", "\n")
    if use_crlf:
        new_text = new_text.replace("\n", "\r\n")

    new_quoted = '"' + new_text.replace('"', '""') + '"'
    new_form_text = form_text[:best_start] + new_quoted + form_text[end_pos:]
    new_form_bytes = BOM_UTF8 + new_form_text.encode("utf-8")

    new_files = [(k, new_form_bytes if k == form_key else v) for k, v in files]
    out = write_container(new_files, compress=True)
    with open(epf_out, "wb") as f:
        f.write(out)

    print(
        f"Form {form_name!r}: module {len(orig_module)} -> {len(new_text)} chars; "
        f"wrote {epf_out} ({len(out)} bytes)"
    )


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: repack_form_module.py <in.epf> <form_name> <module.bsl> <out.epf>")
        sys.exit(1)
    repack(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
