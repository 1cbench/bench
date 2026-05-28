"""
v8pack - 1C:Enterprise v8 container packer/unpacker.

Handles the v8 container binary format used by 1C:Enterprise 8.x for
External Data Processors (.epf) and External Reports (.erf).

Container format:
  - File header: 16 bytes (magic 0x7FFFFFFF, page_size, file_count, reserved)
  - Sequence of blocks, each: CRLF + "data_hex stored_hex 7fffffff " + CRLF + data
  - Block 0 = TOC with 12-byte entries (attr_start, attr_end, 0x7FFFFFFF)
  - Then file pairs: attribute block (timestamps + UTF-16LE name) + content block
  - Outer content blocks are deflate-compressed and page-aligned
  - Inner containers (.0 module files) are NOT compressed

Usage:
  python v8pack.py unpack input.epf output_dir/
  python v8pack.py pack   source.xml source_folder/ output.epf [--ref ref.epf]
  python v8pack.py pack-simple --ref ref.epf --name MyProc \\
      --module code.bsl --template task.txt --output output.epf
"""

import struct
import zlib
import uuid
import re
import os
import sys
import xml.etree.ElementTree as ET

BOM_UTF8 = b'\xef\xbb\xbf'
V8_MAGIC = 0x7FFFFFFF
DEFAULT_PAGE_SIZE = 512

# Well-known class IDs
CLASS_ID_EDP = 'c3831ec8-d8d5-4f93-8a22-f9bfae07327f'  # ExternalDataProcessor
CLASS_ID_ER = 'e41aff26-25cf-4bb6-b6c1-3f478a75f374'   # ExternalReport
CLASS_ID_TEMPLATE = '3daea016-69b7-4ed4-9453-127911372fe6'
CLASS_ID_FORM = 'd5b0e5ed-256d-401c-9c36-f630cafd8a62'        # EDP form
CLASS_ID_FORM_ER = 'a3b368c0-29e2-11d6-a3c7-0050bae0a776'     # ExternalReport form
FORM_CLASS_IDS = {CLASS_ID_FORM, CLASS_ID_FORM_ER}

# Template type mapping (internal int -> XML string)
TEMPLATE_TYPES = {0: 'BinaryData', 1: 'ActiveDocument', 2: 'SpreadsheetDocument',
                  3: 'HTMLDocument', 4: 'TextDocument', 5: 'GeographicalSchema',
                  6: 'GraphicalSchema', 7: 'DataCompositionSchema',
                  8: 'DataCompositionAppearanceTemplate'}


# ═══════════════════════════════════════════════════════════════════════════
# 1C internal {…} format parser
# ═══════════════════════════════════════════════════════════════════════════

def _parse_internal(text: str) -> list | str | int:
    """Parse the 1C {value,value,...} serialization into Python objects."""
    tokens, _ = _tokenize(text, 0)
    return tokens


def _tokenize(text: str, pos: int):
    """Recursive tokenizer. Returns (parsed_value, new_pos)."""
    result = []
    current_token = ''
    while pos < len(text):
        ch = text[pos]
        if ch in (' ', '\r', '\n', '\t'):
            if current_token:
                result.append(_coerce(current_token))
                current_token = ''
            pos += 1
        elif ch == '{':
            if current_token:
                result.append(_coerce(current_token))
                current_token = ''
            inner, pos = _tokenize(text, pos + 1)
            result.append(inner)
        elif ch == '}':
            if current_token:
                result.append(_coerce(current_token))
                current_token = ''
            return result, pos + 1
        elif ch == ',':
            if current_token:
                result.append(_coerce(current_token))
                current_token = ''
            pos += 1
        elif ch == '"':
            if current_token:
                result.append(_coerce(current_token))
                current_token = ''
            s, pos = _parse_string(text, pos)
            result.append(s)
        else:
            current_token += ch
            pos += 1
    if current_token:
        result.append(_coerce(current_token))
    # Top-level: unwrap single element
    return result[0] if len(result) == 1 else result, pos


def _parse_string(text: str, pos: int) -> tuple[str, int]:
    """Parse a quoted string, handling doubled-quote escapes."""
    assert text[pos] == '"'
    pos += 1
    parts = []
    while pos < len(text):
        ch = text[pos]
        if ch == '"':
            if pos + 1 < len(text) and text[pos + 1] == '"':
                parts.append('"')
                pos += 2
            else:
                pos += 1
                break
        else:
            parts.append(ch)
            pos += 1
    return ''.join(parts), pos


def _coerce(token: str) -> str | int:
    """Coerce a bare token to int if numeric, else leave as string."""
    try:
        return int(token)
    except ValueError:
        return token


# ═══════════════════════════════════════════════════════════════════════════
# Low-level v8 container I/O
# ═══════════════════════════════════════════════════════════════════════════

def _deflate_compress(data: bytes) -> bytes:
    c = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


def _deflate_decompress(data: bytes) -> bytes:
    return zlib.decompress(data, -15)


def _block_header(data_size: int, stored_size: int) -> bytes:
    return f'\r\n{data_size:08x} {stored_size:08x} 7fffffff \r\n'.encode('ascii')


def _attr_block(name: str, timestamp: int = 0) -> bytes:
    ts = struct.pack('<Q', timestamp)
    return ts + ts + b'\x00' * 4 + name.encode('utf-16-le') + b'\x00' * 4


def read_container(data: bytes) -> list[tuple[str, bytes]]:
    """Parse v8 container → list of (name, content) pairs (content decompressed)."""
    if data[:4] != struct.pack('<I', V8_MAGIC):
        raise ValueError('Not a v8 container')
    pos = 0x10
    blocks = []
    while pos < len(data):
        if data[pos:pos + 2] != b'\r\n':
            break
        pos += 2
        crlf = data.find(b'\r\n', pos)
        if crlf == -1:
            break
        parts = data[pos:crlf].decode('ascii').strip().split()
        ds, ss = int(parts[0], 16), int(parts[1], 16)
        pos = crlf + 2
        blocks.append((ds, ss, data[pos:pos + ss]))
        pos += ss
    files = []
    for i in range(1, len(blocks), 2):
        if i + 1 >= len(blocks):
            break
        a_ds, _, a_raw = blocks[i]
        name = a_raw[:a_ds][20:].decode('utf-16-le').rstrip('\x00')
        c_ds, _, c_raw = blocks[i + 1]
        raw = c_raw[:c_ds]
        try:
            content = _deflate_decompress(raw)
        except zlib.error:
            content = raw
        files.append((name, content))
    return files


def write_container(files: list[tuple[str, bytes]],
                    page_size: int = DEFAULT_PAGE_SIZE,
                    compress: bool = True,
                    timestamp: int = 0) -> bytes:
    """Build v8 container binary from (name, content) pairs."""
    n = len(files)
    attrs, contents = [], []
    for name, content in files:
        attrs.append(_attr_block(name, timestamp))
        c = _deflate_compress(content) if compress else content
        contents.append(c)

    toc_ds = n * 12
    toc_ss = max(toc_ds, page_size)
    toc_hdr = _block_header(toc_ds, toc_ss)
    data_start = 16 + len(toc_hdr) + toc_ss

    toc_entries = []
    pos = data_start
    for i in range(n):
        a_ds = len(attrs[i])
        c_len = len(contents[i])
        c_ss = max(c_len, page_size) if c_len < page_size else c_len
        a_hdr = _block_header(a_ds, a_ds)
        c_hdr = _block_header(c_len, c_ss)
        toc_entries.append((pos, pos + len(a_hdr) + a_ds))
        pos += len(a_hdr) + a_ds + len(c_hdr) + c_ss

    buf = bytearray()
    buf += struct.pack('<IIII', V8_MAGIC, page_size, n, 0)
    buf += toc_hdr
    toc = bytearray()
    for s, e in toc_entries:
        toc += struct.pack('<III', s, e, V8_MAGIC)
    toc += b'\x00' * (toc_ss - len(toc))
    buf += toc

    for i in range(n):
        a = attrs[i]
        buf += _block_header(len(a), len(a))
        buf += a
        c = contents[i]
        c_ss = max(len(c), page_size) if len(c) < page_size else len(c)
        buf += _block_header(len(c), c_ss)
        buf += c
        buf += b'\x00' * (c_ss - len(c))
    return bytes(buf)


# ═══════════════════════════════════════════════════════════════════════════
# Module container helpers (.0 nested containers)
# ═══════════════════════════════════════════════════════════════════════════

def make_module_container(bsl_content: bytes) -> bytes:
    """Wrap BSL code in a nested v8 container (info + text)."""
    info = BOM_UTF8 + b'{3,1,0,"",0}'
    if not bsl_content.startswith(BOM_UTF8):
        bsl_content = BOM_UTF8 + bsl_content
    return write_container([('info', info), ('text', bsl_content)],
                           compress=False, timestamp=0)


def extract_module_text(container_data: bytes) -> bytes:
    """Extract BSL text from a nested .0 container."""
    return dict(read_container(container_data)).get('text', b'')


# ═══════════════════════════════════════════════════════════════════════════
# Internal-format content helpers
# ═══════════════════════════════════════════════════════════════════════════

def _content_text(data: bytes) -> str:
    """Decode content bytes to text, stripping BOM."""
    if data[:3] == BOM_UTF8:
        return data[3:].decode('utf-8')
    return data.decode('utf-8')


def _bom(text: str) -> bytes:
    return BOM_UTF8 + text.encode('utf-8')


# ═══════════════════════════════════════════════════════════════════════════
# XML generators (internal format → XML)
# ═══════════════════════════════════════════════════════════════════════════

_XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'
_MD_NS = (
    '<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses"'
    ' xmlns:app="http://v8.1c.ru/8.2/managed-application/core"'
    ' xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config"'
    ' xmlns:cmi="http://v8.1c.ru/8.2/managed-application/cmi"'
    ' xmlns:ent="http://v8.1c.ru/8.1/data/enterprise"'
    ' xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform"'
    ' xmlns:style="http://v8.1c.ru/8.1/data/ui/style"'
    ' xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system"'
    ' xmlns:v8="http://v8.1c.ru/8.1/data/core"'
    ' xmlns:v8ui="http://v8.1c.ru/8.1/data/ui"'
    ' xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web"'
    ' xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows"'
    ' xmlns:xen="http://v8.1c.ru/8.3/xcf/enums"'
    ' xmlns:xpr="http://v8.1c.ru/8.3/xcf/predef"'
    ' xmlns:xr="http://v8.1c.ru/8.3/xcf/readable"'
    ' xmlns:xs="http://www.w3.org/2001/XMLSchema"'
    ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
    ' version="2.20">'
)


def _synonym_xml(name: str, indent: str = '\t\t\t') -> str:
    return (f'{indent}<Synonym>\n'
            f'{indent}\t<v8:item>\n'
            f'{indent}\t\t<v8:lang>ru</v8:lang>\n'
            f'{indent}\t\t<v8:content>{name}</v8:content>\n'
            f'{indent}\t</v8:item>\n'
            f'{indent}</Synonym>')


def generate_root_xml(proc_uuid: str, class_id: str, obj_id: str,
                      type_id: str, value_id: str,
                      name: str, synonym: str,
                      form_names: list[str],
                      template_names: list[str],
                      default_form_ref: str) -> str:
    """Generate the root ExternalDataProcessor XML."""
    child_lines = ''.join(f'\t\t\t<Form>{fn}</Form>\n' for fn in form_names)
    child_lines += ''.join(f'\t\t\t<Template>{tn}</Template>\n' for tn in template_names)
    default_form = f'ExternalDataProcessor.{name}.Form.{default_form_ref}' if default_form_ref else ''
    return (
        f'\ufeff{_XML_HEADER}'
        f'{_MD_NS}\n'
        f'\t<ExternalDataProcessor uuid="{proc_uuid}">\n'
        f'\t\t<InternalInfo>\n'
        f'\t\t\t<xr:ContainedObject>\n'
        f'\t\t\t\t<xr:ClassId>{class_id}</xr:ClassId>\n'
        f'\t\t\t\t<xr:ObjectId>{obj_id}</xr:ObjectId>\n'
        f'\t\t\t</xr:ContainedObject>\n'
        f'\t\t\t<xr:GeneratedType name="ExternalDataProcessorObject.{name}" category="Object">\n'
        f'\t\t\t\t<xr:TypeId>{type_id}</xr:TypeId>\n'
        f'\t\t\t\t<xr:ValueId>{value_id}</xr:ValueId>\n'
        f'\t\t\t</xr:GeneratedType>\n'
        f'\t\t</InternalInfo>\n'
        f'\t\t<Properties>\n'
        f'\t\t\t<Name>{name}</Name>\n'
        f'{_synonym_xml(synonym)}\n'
        f'\t\t\t<Comment/>\n'
        f'\t\t\t<DefaultForm>{default_form}</DefaultForm>\n'
        f'\t\t\t<AuxiliaryForm/>\n'
        f'\t\t</Properties>\n'
        f'\t\t<ChildObjects>\n'
        f'{child_lines}'
        f'\t\t</ChildObjects>\n'
        f'\t</ExternalDataProcessor>\n'
        f'</MetaDataObject>'
    )


def generate_form_xml(form_uuid: str, form_name: str, form_synonym: str) -> str:
    return (
        f'\ufeff{_XML_HEADER}'
        f'{_MD_NS}\n'
        f'\t<Form uuid="{form_uuid}">\n'
        f'\t\t<Properties>\n'
        f'\t\t\t<Name>{form_name}</Name>\n'
        f'{_synonym_xml(form_synonym)}\n'
        f'\t\t\t<Comment/>\n'
        f'\t\t\t<FormType>Managed</FormType>\n'
        f'\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents>\n'
        f'\t\t\t<UsePurposes>\n'
        f'\t\t\t\t<v8:Value xsi:type="app:ApplicationUsePurpose">PlatformApplication</v8:Value>\n'
        f'\t\t\t\t<v8:Value xsi:type="app:ApplicationUsePurpose">MobilePlatformApplication</v8:Value>\n'
        f'\t\t\t</UsePurposes>\n'
        f'\t\t\t<ExtendedPresentation/>\n'
        f'\t\t</Properties>\n'
        f'\t</Form>\n'
        f'</MetaDataObject>'
    )


def generate_template_xml(tmpl_uuid: str, tmpl_name: str,
                          tmpl_synonym: str, tmpl_type: str) -> str:
    return (
        f'\ufeff{_XML_HEADER}'
        f'{_MD_NS}\n'
        f'\t<Template uuid="{tmpl_uuid}">\n'
        f'\t\t<Properties>\n'
        f'\t\t\t<Name>{tmpl_name}</Name>\n'
        f'{_synonym_xml(tmpl_synonym)}\n'
        f'\t\t\t<Comment/>\n'
        f'\t\t\t<TemplateType>{tmpl_type}</TemplateType>\n'
        f'\t\t</Properties>\n'
        f'\t</Template>\n'
        f'</MetaDataObject>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# EPF metadata generators (for packing)
# ═══════════════════════════════════════════════════════════════════════════

def _gen_metadata(name: str, synonym: str) -> bytes:
    return _bom(
        '{1,\r\n'
        '{6716b2e8-ac1e-4526-b84c-b98fe2530ba6},1,\r\n'
        '{c3831ec8-d8d5-4f93-8a22-f9bfae07327f,\r\n'
        '{1,\r\n'
        '{4,bb65a9aa-a2fc-45c4-8fae-b5a60a61d8af,6012e964-10d0-4b53-a4c5-0f173dd62b51,\r\n'
        '{0,\r\n'
        '{3,\r\n'
        f'{{1,0,21a03683-18a3-443d-8fb6-f690448a91a5}},"{name}",\r\n'
        f'{{1,"ru","{synonym}"}},"",0,0,00000000-0000-0000-0000-000000000000,0}}\r\n'
        '},f9de4826-d24e-42c5-8313-2a56bb7025f8,"",00000000-0000-0000-0000-000000000000},4,\r\n'
        '{2bcef0d1-0981-11d6-b9b8-0050bae0a95d,0},\r\n'
        '{3daea016-69b7-4ed4-9453-127911372fe6,1,981b75cf-897a-44fd-bb45-26bad947d9df},\r\n'
        '{d5b0e5ed-256d-401c-9c36-f630cafd8a62,1,f9de4826-d24e-42c5-8313-2a56bb7025f8},\r\n'
        '{ec6bb5e5-b7a8-4d75-bec9-658107a699cf,0}\r\n'
        '}\r\n'
        '}\r\n'
        '}'
    )


def _gen_copyinfo(name: str) -> bytes:
    return _bom(
        '{4,\r\n'
        '{2,\r\n'
        '{21a03683-18a3-443d-8fb6-f690448a91a5,21a03683-18a3-443d-8fb6-f690448a91a5,1,\r\n'
        f'{{c3831ec8-d8d5-4f93-8a22-f9bfae07327f,"{name}"}}\r\n'
        '},\r\n'
        '{f9de4826-d24e-42c5-8313-2a56bb7025f8,f9de4826-d24e-42c5-8313-2a56bb7025f8,1,\r\n'
        '{d5b0e5ed-256d-401c-9c36-f630cafd8a62,"Форма"}\r\n'
        '}\r\n'
        '},\r\n'
        '{1,\r\n'
        '{bb65a9aa-a2fc-45c4-8fae-b5a60a61d8af,21a03683-18a3-443d-8fb6-f690448a91a5,0}\r\n'
        '},\r\n'
        '{0},\r\n'
        '{0,0},\r\n'
        '{0}\r\n'
        '}'
    )


_TEMPLATE_META = _bom(
    '{1,\r\n'
    '{2,4,\r\n'
    '{3,\r\n'
    '{1,0,981b75cf-897a-44fd-bb45-26bad947d9df},"Задача",\r\n'
    '{1,"ru","Задача"},"",0,0,00000000-0000-0000-0000-000000000000,0}\r\n'
    '},0}'
)

_FORM_META = _bom(
    '{1,\r\n'
    '{1,\r\n'
    '{0,\r\n'
    '{13,\r\n'
    '{3,\r\n'
    '{1,0,f9de4826-d24e-42c5-8313-2a56bb7025f8},"Форма",\r\n'
    '{1,"ru","Форма"},"",0,0,00000000-0000-0000-0000-000000000000,0},0,1,\r\n'
    '{2,\r\n'
    '{"#",1708fdaa-cbce-4289-b373-07a5a74bee91,1},\r\n'
    '{"#",1708fdaa-cbce-4289-b373-07a5a74bee91,2}\r\n'
    '}\r\n'
    '},\r\n'
    '{0}\r\n'
    '}\r\n'
    '},0}'
)

_ROOT = _bom('{2,6716b2e8-ac1e-4526-b84c-b98fe2530ba6,}')
_VERSION = _bom('{\r\n{216,0,\r\n{80327,0}\r\n}\r\n}')


def _gen_versions() -> bytes:
    names = [
        '21a03683-18a3-443d-8fb6-f690448a91a5.0',
        '6716b2e8-ac1e-4526-b84c-b98fe2530ba6',
        '981b75cf-897a-44fd-bb45-26bad947d9df',
        '981b75cf-897a-44fd-bb45-26bad947d9df.0',
        'copyinfo',
        'f9de4826-d24e-42c5-8313-2a56bb7025f8',
        'f9de4826-d24e-42c5-8313-2a56bb7025f8.0',
        'root', 'version', 'versions',
    ]
    pairs = ','.join(f'{uuid.uuid4()},"{n}"' for n in names)
    return _bom(f'{{1,{len(names) + 1},"",{pairs},{uuid.uuid4()}}}')


# ═══════════════════════════════════════════════════════════════════════════
# Metadata parsing (internal format → structured data)
# ═══════════════════════════════════════════════════════════════════════════

def _extract_metadata_fields(files: dict[str, bytes]) -> dict:
    """Extract structured metadata from internal-format container files."""
    info = {}

    # --- root ---
    root_text = _content_text(files['root'])
    root_parsed = _parse_internal(root_text)
    # root = [2, "uuid", ""]  →  uuid is the main metadata entry
    info['proc_uuid'] = root_parsed[1]

    # --- main metadata (6716b2e8…) ---
    meta_key = info['proc_uuid']
    meta_text = _content_text(files[meta_key])
    meta = _parse_internal(meta_text)
    # meta = [1, [proc_uuid], 1, [class_id, [1, [4, type_id, value_id, ...]]]]
    info['class_id'] = meta[3][0]
    inner = meta[3][1]  # [1, [4, type_id, value_id, ...]]
    props = inner[1]    # [4, type_id, value_id, ...]
    info['type_id'] = props[1]
    info['value_id'] = props[2]

    # props[3] = [0, [3, [1,0,obj_id], "name", [1,"ru","synonym"], ...]]
    # props[4] = default_form_uuid
    obj_block = props[3]
    contained = obj_block[1]  # [3, [1,0,obj_id], "name", [1,"ru","syn"], ...]
    info['obj_id'] = contained[1][2]
    info['name'] = contained[2]
    info['synonym'] = contained[3][2] if isinstance(contained[3], list) else contained[2]

    # default form uuid (at props[4])
    info['default_form_uuid'] = props[4] if len(props) > 4 else ''

    # child objects: inner[2] = count, inner[3:] = entries.
    # Each entry is a flat list [class_uuid, count, uuid_1, uuid_2, ..., uuid_N]
    # (a single class entry can declare multiple children, e.g. several Templates).
    child_entries = inner[3:]
    info['forms'] = {}
    info['templates'] = {}
    for entry in child_entries:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        cid = entry[0]
        count = entry[1]
        if not isinstance(count, int) or count <= 0:
            continue
        child_uuids = entry[2:2 + count]
        for child_uuid in child_uuids:
            # Some bench EPFs (e.g. task_003 with Реквизиты/Команды entries)
            # embed a structured list instead of a flat UUID for child class
            # ids we don't unpack — skip them. Forms/Templates remain string
            # UUIDs and are processed normally.
            if not isinstance(child_uuid, str) or child_uuid not in files:
                continue
            if cid in FORM_CLASS_IDS:
                fm = _parse_internal(_content_text(files[child_uuid]))
                # [1, [1, [0, [13, [3, [1,0,uuid],"Name",[1,"ru","Syn"],...], ...], [0]]], 0]
                try:
                    form_desc = fm[1][1][1][1]  # [3, [1,0,uuid], "Name", ...]
                    info['forms'][child_uuid] = {
                        'name': form_desc[2],
                        'synonym': form_desc[3][2] if isinstance(form_desc[3], list) else form_desc[2],
                    }
                except (IndexError, TypeError):
                    info['forms'][child_uuid] = {'name': 'Form', 'synonym': 'Form'}
            elif cid == CLASS_ID_TEMPLATE:
                tm = _parse_internal(_content_text(files[child_uuid]))
                # [1, [2, 4, [3, [1,0,uuid], "Name", [1,"ru","Syn"], ...]], 0]
                try:
                    tmpl_type_int = tm[1][1]
                    tmpl_desc = tm[1][2]  # [3, [1,0,uuid], "Name", ...]
                    info['templates'][child_uuid] = {
                        'name': tmpl_desc[2],
                        'synonym': tmpl_desc[3][2] if isinstance(tmpl_desc[3], list) else tmpl_desc[2],
                        'type': TEMPLATE_TYPES.get(tmpl_type_int, 'TextDocument'),
                    }
                except (IndexError, TypeError):
                    info['templates'][child_uuid] = {
                        'name': 'Template', 'synonym': 'Template', 'type': 'TextDocument'}

    # Resolve default form name
    info['default_form_name'] = ''
    if info['default_form_uuid'] and info['default_form_uuid'] in info['forms']:
        info['default_form_name'] = info['forms'][info['default_form_uuid']]['name']

    return info


def _extract_form_module(form_data_text: str) -> str:
    """
    Extract the BSL module text embedded in the serialized form data {4,...}.

    The form serialization stores the module as one of the top-level string
    values near the end of the structure.  We search for 1C BSL directive
    markers (&НаСервере, &НаКлиенте, etc.) to locate it.
    """
    # BSL directives that can start a module
    directives = ('&НаСервере', '&НаКлиенте', '&НаСервереБезКонтекста',
                  '&НаКлиентеНаСервере', '&НаКлиентеНаСервереБезКонтекста')

    # Find the earliest directive occurrence that's inside a quoted string
    best_start = -1
    for d in directives:
        idx = form_data_text.find(f'"{d}')
        if idx != -1 and (best_start == -1 or idx < best_start):
            best_start = idx

    if best_start == -1:
        return ''

    # Parse the quoted string starting at best_start
    module_text, _ = _parse_string(form_data_text, best_start)
    return module_text


# ═══════════════════════════════════════════════════════════════════════════
# Unpack EPF → XML folder structure
# ═══════════════════════════════════════════════════════════════════════════

def unpack_epf(epf_path: str, output_dir: str) -> None:
    """
    Unpack an EPF into the XML folder structure matching 1C Designer export:

        <name>.xml
        <name>/
          Ext/ObjectModule.bsl
          Forms/<FormName>.xml
          Forms/<FormName>/Ext/Form.xml       (internal format — not convertible)
          Forms/<FormName>/Ext/Form/Module.bsl
          Templates/<TmplName>.xml
          Templates/<TmplName>/Ext/Template.txt
    """
    with open(epf_path, 'rb') as f:
        data = f.read()

    container_files = dict(read_container(data))
    info = _extract_metadata_fields(container_files)

    proc_name = info['name']
    print(f'Processing: {proc_name} ("{info["synonym"]}")')

    # --- Root XML ---
    root_xml = generate_root_xml(
        proc_uuid=info['proc_uuid'],
        class_id=info['class_id'],
        obj_id=info['obj_id'],
        type_id=info['type_id'],
        value_id=info['value_id'],
        name=proc_name,
        synonym=info['synonym'],
        form_names=[f['name'] for f in info['forms'].values()],
        template_names=[t['name'] for t in info['templates'].values()],
        default_form_ref=info['default_form_name'],
    )
    root_xml_path = os.path.join(output_dir, f'{proc_name}.xml')
    os.makedirs(output_dir, exist_ok=True)
    with open(root_xml_path, 'w', encoding='utf-8-sig') as f:
        f.write(root_xml.lstrip('\ufeff'))
    print(f'  {proc_name}.xml')

    proc_dir = os.path.join(output_dir, proc_name)

    # --- ObjectModule.bsl ---
    obj_id = info['obj_id']
    module_key = f'{obj_id}.0'
    if module_key in container_files:
        module_data = container_files[module_key]
        if module_data[:4] == struct.pack('<I', V8_MAGIC):
            bsl = extract_module_text(module_data)
        else:
            bsl = module_data
        mod_dir = os.path.join(proc_dir, 'Ext')
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, 'ObjectModule.bsl'), 'wb') as f:
            f.write(bsl)
        print(f'  Ext/ObjectModule.bsl ({len(bsl)} bytes)')

    # --- Forms ---
    for form_uuid, form_info in info['forms'].items():
        fname = form_info['name']

        # Form metadata XML
        form_meta_xml = generate_form_xml(form_uuid, fname, form_info['synonym'])
        form_dir = os.path.join(proc_dir, 'Forms')
        os.makedirs(form_dir, exist_ok=True)
        with open(os.path.join(form_dir, f'{fname}.xml'), 'w', encoding='utf-8-sig') as f:
            f.write(form_meta_xml.lstrip('\ufeff'))
        print(f'  Forms/{fname}.xml')

        # Form data (.0)
        form_data_key = f'{form_uuid}.0'
        if form_data_key in container_files:
            form_data = container_files[form_data_key]
            form_ext = os.path.join(proc_dir, 'Forms', fname, 'Ext')
            os.makedirs(form_ext, exist_ok=True)

            # Save the internal form data (cannot convert to XML)
            with open(os.path.join(form_ext, 'Form.bin'), 'wb') as f:
                f.write(form_data)
            print(f'  Forms/{fname}/Ext/Form.bin (internal format, {len(form_data)} bytes)')

            # Try to extract Module.bsl from form data
            form_text = _content_text(form_data)
            module_text = _extract_form_module(form_text)
            if module_text:
                mod_path = os.path.join(form_ext, 'Form')
                os.makedirs(mod_path, exist_ok=True)
                with open(os.path.join(mod_path, 'Module.bsl'), 'w',
                          encoding='utf-8-sig', newline='') as f:
                    f.write(module_text)
                print(f'  Forms/{fname}/Ext/Form/Module.bsl ({len(module_text)} chars)')

    # --- Templates ---
    for tmpl_uuid, tmpl_info in info['templates'].items():
        tname = tmpl_info['name']

        # Template metadata XML
        tmpl_meta_xml = generate_template_xml(
            tmpl_uuid, tname, tmpl_info['synonym'], tmpl_info['type'])
        tmpl_dir = os.path.join(proc_dir, 'Templates')
        os.makedirs(tmpl_dir, exist_ok=True)
        with open(os.path.join(tmpl_dir, f'{tname}.xml'), 'w', encoding='utf-8-sig') as f:
            f.write(tmpl_meta_xml.lstrip('\ufeff'))
        print(f'  Templates/{tname}.xml')

        # Template data (.0)
        tmpl_data_key = f'{tmpl_uuid}.0'
        if tmpl_data_key in container_files:
            tmpl_data = container_files[tmpl_data_key]
            tmpl_ext = os.path.join(proc_dir, 'Templates', tname, 'Ext')
            os.makedirs(tmpl_ext, exist_ok=True)
            ext_name = 'Template.txt' if tmpl_info['type'] == 'TextDocument' else 'Template.bin'
            with open(os.path.join(tmpl_ext, ext_name), 'wb') as f:
                f.write(tmpl_data)
            print(f'  Templates/{tname}/Ext/{ext_name} ({len(tmpl_data)} bytes)')

    print(f'\nUnpacked to: {output_dir}')


# ═══════════════════════════════════════════════════════════════════════════
# Pack EPF
# ═══════════════════════════════════════════════════════════════════════════

def build_epf(name: str, synonym: str,
              module_bsl: bytes, template_content: bytes,
              form_data: bytes,
              timestamp: int = 0x0002453a01193430) -> bytes:
    """Build EPF binary from components."""
    module_container = make_module_container(module_bsl)
    metadata = _gen_metadata(name, synonym)
    copyinfo = _gen_copyinfo(name)
    versions = _gen_versions()
    if not template_content.startswith(BOM_UTF8):
        template_content = BOM_UTF8 + template_content
    if not form_data.startswith(BOM_UTF8):
        form_data = BOM_UTF8 + form_data

    files = [
        ('21a03683-18a3-443d-8fb6-f690448a91a5.0', module_container),
        ('6716b2e8-ac1e-4526-b84c-b98fe2530ba6', metadata),
        ('981b75cf-897a-44fd-bb45-26bad947d9df', _TEMPLATE_META),
        ('981b75cf-897a-44fd-bb45-26bad947d9df.0', template_content),
        ('copyinfo', copyinfo),
        ('f9de4826-d24e-42c5-8313-2a56bb7025f8', _FORM_META),
        ('f9de4826-d24e-42c5-8313-2a56bb7025f8.0', form_data),
        ('root', _ROOT),
        ('version', _VERSION),
        ('versions', versions),
    ]
    return write_container(files, compress=True, timestamp=timestamp)


def pack_epf_from_source(root_xml_path: str, source_folder: str,
                         output_path: str,
                         ref_epf_path: str | None = None) -> None:
    """Pack EPF from the XML folder structure (needs reference EPF for form data)."""
    tree = ET.parse(root_xml_path)
    root = tree.getroot()
    ns = {'md': 'http://v8.1c.ru/8.3/MDClasses'}
    edp = root.find('md:ExternalDataProcessor', ns)
    if edp is None:
        raise ValueError('Root XML has no ExternalDataProcessor element')

    proc_name = edp.find('md:Properties/md:Name', ns).text
    ns_v8 = {'v8': 'http://v8.1c.ru/8.1/data/core'}
    synonym = proc_name
    syn_el = edp.find('md:Properties/md:Synonym', ns)
    if syn_el is not None:
        c = syn_el.find('.//v8:content', ns_v8)
        if c is not None and c.text:
            synonym = c.text

    print(f'Processing: {proc_name} ("{synonym}")')

    module_bsl = open(os.path.join(source_folder, 'Ext', 'ObjectModule.bsl'), 'rb').read()
    print(f'  ObjectModule: {len(module_bsl)} bytes')

    template_path = os.path.join(source_folder, 'Templates', 'Задача', 'Ext', 'Template.txt')
    template_content = open(template_path, 'rb').read()
    print(f'  Template: {len(template_content)} bytes')

    # Form data from reference EPF
    form_data = _resolve_form_data(ref_epf_path, root_xml_path)

    epf = build_epf(proc_name, synonym, module_bsl, template_content, form_data)
    with open(output_path, 'wb') as f:
        f.write(epf)
    print(f'  Written: {output_path} ({len(epf)} bytes)')


def _resolve_form_data(ref_epf_path: str | None, root_xml_path: str) -> bytes:
    """Get form data from a reference EPF or template.epf fallback."""
    form_key = 'f9de4826-d24e-42c5-8313-2a56bb7025f8.0'

    def _find_form_data(files: dict) -> bytes:
        if form_key in files:
            return files[form_key]
        # Fallback: find the form data by heuristic (large .0 with medium-sized metadata)
        for key, value in files.items():
            if not key.endswith('.0') or key == 'copyinfo':
                continue
            base = key[:-2]
            if base in files and len(files[base]) > 200 and len(value) > 3000:
                return value
        raise KeyError(f'Form data key not found in EPF')

    if ref_epf_path:
        ref_files = dict(read_container(open(ref_epf_path, 'rb').read()))
        print(f'  Form data from: {ref_epf_path}')
        return _find_form_data(ref_files)
    fallback = os.path.join(os.path.dirname(root_xml_path), 'template.epf')
    if os.path.exists(fallback):
        ref_files = dict(read_container(open(fallback, 'rb').read()))
        print(f'  Form data from: {fallback}')
        return _find_form_data(ref_files)
    raise FileNotFoundError(
        'No reference EPF provided and no template.epf found. '
        'Use --ref to specify one (form data cannot be generated from XML).')


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'unpack':
        if len(sys.argv) < 4:
            print('Usage: v8pack.py unpack <input.epf> <output_dir/>')
            sys.exit(1)
        unpack_epf(sys.argv[2], sys.argv[3])

    elif cmd == 'pack':
        if len(sys.argv) < 5:
            print('Usage: v8pack.py pack <source.xml> <source_folder/> <output.epf> [--ref ref.epf]')
            sys.exit(1)
        ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else None
        pack_epf_from_source(sys.argv[2], sys.argv[3], sys.argv[4], ref)

    elif cmd == 'pack-simple':
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument('cmd')
        p.add_argument('--ref', required=True)
        p.add_argument('--name', required=True)
        p.add_argument('--synonym', default=None)
        p.add_argument('--module', required=True)
        p.add_argument('--template', required=True)
        p.add_argument('--output', required=True)
        a = p.parse_args()
        form_data = dict(read_container(open(a.ref, 'rb').read()))[
            'f9de4826-d24e-42c5-8313-2a56bb7025f8.0']
        epf = build_epf(a.name, a.synonym or a.name,
                        open(a.module, 'rb').read(),
                        open(a.template, 'rb').read(), form_data)
        with open(a.output, 'wb') as f:
            f.write(epf)
        print(f'Written: {a.output} ({len(epf)} bytes)')

    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
