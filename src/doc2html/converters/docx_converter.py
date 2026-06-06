"""Word (.docx) 轉換器。

用 python-docx 走訪段落與表格，依樣式（Heading 1~6、List 等）對應到
語意化的 HTML 標籤，並把粗體/斜體等行內格式重建為 <strong>/<em>。
"""

from __future__ import annotations

import re
from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException
from .._html_builder import escape, table
from .._stream_info import StreamInfo

_DOCX_EXT = ".docx"
_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class DocxConverter(DocumentConverter):
    priority = 5.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext == _DOCX_EXT or mime == _DOCX_MIME

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        try:
            import docx  # noqa: PLC0415
            from docx.document import Document as _Doc  # noqa: PLC0415,F401
            from docx.oxml.table import CT_Tbl  # noqa: PLC0415
            from docx.oxml.text.paragraph import CT_P  # noqa: PLC0415
            from docx.table import Table  # noqa: PLC0415
            from docx.text.paragraph import Paragraph  # noqa: PLC0415
        except ImportError as exc:
            raise MissingDependencyException(
                "DocxConverter 需要 python-docx，請執行："
                "pip install 'doc2html[docx]'"
            ) from exc

        document = docx.Document(file_stream)
        parts: list[str] = []
        title = None

        # 連續清單項的緩衝：(清單標籤 ul/ol, [<li>...,<li>...])
        list_tag: str = ""
        list_items: list[str] = []

        def flush_list() -> None:
            nonlocal list_tag, list_items
            if list_items:
                parts.append(
                    f"<{list_tag}>" + "".join(list_items) + f"</{list_tag}>"
                )
                list_tag, list_items = "", []

        # 依文件內實際順序走訪段落與表格（python-docx 預設兩者分開）
        body = document.element.body
        for child in body.iterchildren():
            if isinstance(child, CT_P):
                para = Paragraph(child, document)
                kind, html = self._paragraph_html(para)
                if not html:
                    continue
                if kind in ("ul", "ol"):
                    # 清單類型改變就先收掉前一個清單
                    if list_items and list_tag != kind:
                        flush_list()
                    list_tag = kind
                    list_items.append(html)
                else:
                    flush_list()
                    parts.append(html)
                    if title is None and _is_heading(para):
                        title = para.text.strip()
            elif isinstance(child, CT_Tbl):
                flush_list()
                tbl = Table(child, document)
                parts.append(self._table_html(tbl))

        flush_list()

        if title is None:
            title = stream_info.filename
        return DocumentConverterResult("\n".join(parts), title=title)

    def _paragraph_html(self, para) -> tuple[str, str]:
        """回傳 (種類, html)。種類為 'ul'/'ol' 時 html 是單一 <li>，
        其餘為 'block'，由呼叫端決定如何組裝。空段落回傳 ('', '')。"""
        inner = self._runs_html(para)
        if not inner.strip():
            return "", ""
        style = (para.style.name if para.style else "") or ""

        heading_match = re.match(r"Heading (\d)", style)
        if heading_match:
            level = min(int(heading_match.group(1)), 6)
            return "block", f"<h{level}>{inner}</h{level}>"
        if style == "Title":
            return "block", f"<h1>{inner}</h1>"
        if style == "Subtitle":
            return "block", f'<p class="subtitle"><em>{inner}</em></p>'
        if "List" in style:
            # 有序清單樣式名通常含 "Number"，其餘視為無序
            tag = "ol" if "Number" in style else "ul"
            return tag, f"<li>{inner}</li>"
        if style in ("Quote", "Intense Quote"):
            return "block", f"<blockquote>{inner}</blockquote>"
        return "block", f"<p>{inner}</p>"

    def _runs_html(self, para) -> str:
        out = []
        for run in para.runs:
            text = escape(run.text)
            if not text:
                continue
            if run.bold:
                text = f"<strong>{text}</strong>"
            if run.italic:
                text = f"<em>{text}</em>"
            if run.underline:
                text = f"<u>{text}</u>"
            out.append(text)
        return "".join(out)

    def _table_html(self, tbl) -> str:
        rows = []
        for row in tbl.rows:
            rows.append([cell.text for cell in row.cells])
        if not rows:
            return ""
        header, *body = rows
        return table(body, header=header)


def _is_heading(para) -> bool:
    style = (para.style.name if para.style else "") or ""
    return style.startswith("Heading") or style in {"Title"}
