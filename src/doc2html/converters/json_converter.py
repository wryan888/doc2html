"""JSON 轉換器：把結構遞迴渲染成巢狀的 HTML 清單／表格。"""

from __future__ import annotations

import json
from typing import Any, BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._html_builder import escape
from .._stream_info import StreamInfo


class JsonConverter(DocumentConverter):
    """把 JSON 物件/陣列渲染成可讀的巢狀結構。"""

    priority = 5.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        if ext == ".json" or mime in {"application/json", "text/json"}:
            return True
        if ext == ".jsonl" or ext == ".ndjson":
            return True
        return False

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        charset = stream_info.charset or "utf-8"
        text = file_stream.read().decode(charset, errors="replace")
        ext = (stream_info.extension or "").lower()

        try:
            if ext in {".jsonl", ".ndjson"}:
                data: Any = [
                    json.loads(line) for line in text.splitlines() if line.strip()
                ]
            else:
                data = json.loads(text)
        except json.JSONDecodeError as exc:
            # 解析失敗就原樣保留，包進 <pre>
            return DocumentConverterResult(
                f"<p><em>JSON 解析失敗：{escape(exc)}</em></p>"
                f"<pre><code>{escape(text)}</code></pre>",
                title=stream_info.filename,
            )

        return DocumentConverterResult(
            _render(data), title=stream_info.filename
        )


def _render(value: Any) -> str:
    """把任意 JSON 值遞迴轉成 HTML。"""
    if isinstance(value, dict):
        if not value:
            return "<code>{}</code>"
        rows = []
        for key, val in value.items():
            rows.append(
                f"<tr><th>{escape(key)}</th><td>{_render(val)}</td></tr>"
            )
        return "<table>\n" + "\n".join(rows) + "\n</table>"
    if isinstance(value, list):
        if not value:
            return "<code>[]</code>"
        # 全是純量 -> 用逗號列；含結構 -> 用 <ul>
        if all(not isinstance(v, (dict, list)) for v in value):
            items = ", ".join(_render(v) for v in value)
            return f"<code>[{items}]</code>"
        items = "".join(f"<li>{_render(v)}</li>" for v in value)
        return f"<ul>{items}</ul>"
    if isinstance(value, bool):
        return f"<code>{'true' if value else 'false'}</code>"
    if value is None:
        return "<code>null</code>"
    if isinstance(value, (int, float)):
        return f"<code>{escape(value)}</code>"
    return escape(value)
