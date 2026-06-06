"""Word (.docx) 轉換器。

用 python-docx 走訪段落與表格，依樣式（Heading 1~6、List 等）對應到
語意化的 HTML 標籤，並把粗體/斜體等行內格式重建為 <strong>/<em>。

v0.2 起額外處理：
- 超連結（w:hyperlink）→ <a href>（外部連結用 rels 解析，內部錨點用 #anchor）
- 內嵌圖片（w:drawing/a:blip）→ <img> base64 data URI

v0.3 起：
- 書籤（w:bookmarkStart）→ <a id="name">，讓內部錨點連結真正能跳轉
"""

from __future__ import annotations

import re
from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException
from .._html_builder import escape, image_data_uri, table
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
        inner = self._paragraph_inner(para)
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

    def _paragraph_inner(self, para) -> str:
        """依 XML 順序走訪段落子節點，處理書籤、一般 run 與超連結。"""
        from docx.oxml.ns import qn  # noqa: PLC0415
        from docx.text.run import Run  # noqa: PLC0415

        out = []
        for child in para._p:
            if child.tag == qn("w:bookmarkStart"):
                anchor = self._bookmark_anchor(child, qn)
                if anchor:
                    out.append(anchor)
            elif child.tag == qn("w:r"):
                out.append(self._format_run(Run(child, para), para))
            elif child.tag == qn("w:hyperlink"):
                out.append(self._hyperlink_html(child, para, qn, Run))
        return "".join(out)

    def _bookmark_anchor(self, bm_element, qn) -> str:
        """w:bookmarkStart → <a id="name">，作為內部錨點的跳轉目標。

        Word 的目錄/交叉參考用書籤名（如 _Toc123）當錨點，對應到
        v0.2 已支援的 <a href="#name">。略過 Word 自動插入的 _GoBack。
        """
        name = bm_element.get(qn("w:name"))
        if not name or name == "_GoBack":
            return ""
        return f'<a id="{escape(name)}"></a>'

    def _format_run(self, run, para) -> str:
        """單一 run → HTML：優先輸出內嵌圖片，否則套用粗/斜/底線。"""
        img = self._run_image_html(run, para)
        if img:
            return img
        text = escape(run.text)
        if not text:
            return ""
        if run.bold:
            text = f"<strong>{text}</strong>"
        if run.italic:
            text = f"<em>{text}</em>"
        if run.underline:
            text = f"<u>{text}</u>"
        return text

    def _run_image_html(self, run, para) -> str:
        """抽出 run 內的內嵌圖片，回傳 <img> data URI（找不到回傳空字串）。"""
        from docx.oxml.ns import qn  # noqa: PLC0415

        blips = run._element.findall(".//" + qn("a:blip"))
        out = []
        for blip in blips:
            rid = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
            if not rid:
                continue
            try:
                image_part = para.part.related_parts[rid]
            except KeyError:
                continue
            blob = image_part.blob
            if not self.embed_images or len(blob) > self.max_image_bytes:
                out.append("<em>[圖片]</em>")
                continue
            out.append(image_data_uri(blob, image_part.content_type, alt=""))
        return "".join(out)

    def _hyperlink_html(self, h_element, para, qn, Run) -> str:
        """w:hyperlink → <a>。外部連結走 rels，內部錨點走 #anchor。"""
        inner = "".join(
            self._format_run(Run(r, para), para)
            for r in h_element.findall(qn("w:r"))
        )
        if not inner:
            return ""
        rid = h_element.get(qn("r:id"))
        if rid:
            try:
                url = para.part.rels[rid].target_ref
            except KeyError:
                url = None
            if url:
                return f'<a href="{escape(url)}">{inner}</a>'
        anchor = h_element.get(qn("w:anchor"))
        if anchor:
            return f'<a href="#{escape(anchor)}">{inner}</a>'
        return inner

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
