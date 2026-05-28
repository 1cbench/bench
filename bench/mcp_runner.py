"""
McpRunner — replacement for OneCEngine.run_processing.

Instead of launching 1C:Enterprise via SampleOpener.epf and waiting for the
processing to write its result to a log file, we drive 1C through the MCP
Toolkit (HTTP, streamable-http transport). The toolkit's execute_code tool
runs a one-shot BSL snippet that:

  1. loads the patched .epf into temp storage;
  2. connects it as a runtime ExternalDataProcessor;
  3. invokes the entry point (ЗапуститьРешение) inside a Попытка block;
  4. returns "Result: true|false" on success or "Error: ..." on exception.

The raw result string is parsed back into the same {compiled, success,
error, raw_result} contract the rest of the bench expects. This keeps the
compiled/runtime-error conflation behaviour identical to the log-based
flow it replaces.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# Host ↔ MCP path translation. When the MCP server runs in a docker container
# (see dockerize/), Windows paths the host uses aren't visible inside the
# container — we bind-mount the project root and translate paths at call time.
# Same env-var contract bench_agentic/bench_paths.py uses, so a single shell
# setup (BENCH_MCP_ROOT=/host/dev) covers both runners.
# parents: [0]=bench (package), [1]=bench (project root), [2]=1cbench, [3]=dev.
# `dev/` is the anchor matched by the docker bind-mount in dockerize/run.ps1.
_HOST_ROOT = Path(
    os.environ.get("BENCH_HOST_ROOT")
    or Path(__file__).resolve().parents[3]
)
_MCP_ROOT = os.environ.get("BENCH_MCP_ROOT", str(_HOST_ROOT))


def _to_mcp_path(host_path: str) -> str:
    """Translate an absolute host path to what the MCP server can open."""
    p = Path(host_path)
    if p.is_absolute():
        try:
            p = p.relative_to(_HOST_ROOT)
        except ValueError:
            return host_path.replace("\\", "/")
    root = _MCP_ROOT.rstrip("/\\").replace("\\", "/")
    return f"{root}/{p.as_posix()}"


def _parse_sse_json(raw: str) -> dict:
    """MCP streamable-http packs each JSON-RPC reply across SSE `data:` lines."""
    lines = raw.strip().splitlines()
    parts: list[str] = []
    for line in lines:
        if line.startswith("data:"):
            parts.append(line[5:].strip())
    if not parts:
        return json.loads(raw)
    return json.loads("\n".join(parts))


class McpRunner:

    def __init__(self, url: str = "http://localhost:6003/mcp"):
        self.url = url
        self.session_id: str | None = None
        self._next_id = 1
        self._initialize()

    def run_epf(self, epf_path: str) -> dict:
        """Execute the patched .epf and return {compiled, success, error, raw_result}."""
        bsl = self._build_run_bsl(_to_mcp_path(epf_path))
        try:
            response = self._call_tool("execute_code", {"code": bsl})
        except Exception as e:
            return {
                "compiled": False,
                "success": False,
                "error": f"mcp transport: {e}",
                "raw_result": "",
            }

        if not response.get("success"):
            err = response.get("error") or "execute_code failed"
            return {
                "compiled": False,
                "success": False,
                "error": str(err),
                "raw_result": "",
            }

        raw = str(response.get("data", ""))
        return self._interpret(raw)

    @staticmethod
    def _interpret(raw: str) -> dict:
        """Match parse_logs() semantics: any "Error:" → not compiled."""
        compiled = "Error:" not in raw
        success = "Result: true" in raw
        error = ""
        if not compiled:
            error = raw.split("Error:", 1)[1].strip()
        return {
            "compiled": compiled,
            "success": success,
            "error": error,
            "raw_result": raw,
        }

    @staticmethod
    def _build_run_bsl(epf_path: str) -> str:
        # 1C string literals don't interpret backslashes, so a Windows path
        # can be embedded as-is. The only character we need to escape is the
        # double-quote (doubled inside 1C strings).
        path_literal = epf_path.replace('"', '""')
        # `Знач` is a reserved modifier in parameter lists (Процедура Foo(Знач P))
        # and the BSL parser rejects it as a bare statement keyword too. Use
        # «Возврат» as the local variable name instead.
        return (
            f'ДвоичныеДанные = Новый ДвоичныеДанные("{path_literal}");\n'
            'АдресХранилища = ПоместитьВоВременноеХранилище(ДвоичныеДанные);\n'
            'Попытка\n'
            '    ИмяОбр = ВнешниеОбработки.Подключить(АдресХранилища, , Ложь);\n'
            '    Обр = ВнешниеОбработки.Создать(ИмяОбр);\n'
            '    Ответ = Обр.ЗапуститьРешение();\n'
            '    Результат = ?(Ответ = Истина, "Result: true", "Result: false");\n'
            'Исключение\n'
            '    Инф = ИнформацияОбОшибке();\n'
            '    Сообщение = Инф.Описание;\n'
            '    Если Инф.Причина <> Неопределено Тогда\n'
            '        Сообщение = Сообщение + ": " + Инф.Причина.Описание;\n'
            '    КонецЕсли;\n'
            '    Результат = "Error: " + Сообщение;\n'
            'КонецПопытки;'
        )

    # ------------------------------------------------------------------
    # MCP protocol plumbing
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        self._post({
            "jsonrpc": "2.0", "id": self._rid(), "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "bench", "version": "1.0"},
            },
        })
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            expect_response=False,
        )
        logger.info("MCP session: %s", self.session_id)

    def _call_tool(self, name: str, arguments: dict) -> dict:
        resp = self._post({
            "jsonrpc": "2.0", "id": self._rid(), "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        for item in resp.get("result", {}).get("content", []):
            if item.get("type") == "text":
                return json.loads(item["text"])
        return resp

    def _post(self, payload: dict, *, expect_response: bool = True) -> dict | None:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "text/event-stream, application/json",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(req)
        sid = resp.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        if not expect_response:
            resp.read()
            return None
        body = resp.read().decode("utf-8")
        return _parse_sse_json(body)

    def _rid(self) -> int:
        r = self._next_id
        self._next_id += 1
        return r
