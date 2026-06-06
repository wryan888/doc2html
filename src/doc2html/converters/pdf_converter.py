"""PDF 轉換器：用 pdfplumber（內含 pdfminer.six）抽取文字與表格。

策略（逐頁）：
1. find_tables() 取出表格與其 bounding box。
2. extract_words() 取出文字詞，過濾掉落在表格框內的詞。
3. 把剩餘的詞依垂直位置分行、再依間距合併成段落；字級偏大的單行視為標題。
4. 把表格與文字段落依垂直位置（top）交錯排序，輸出成符合閱讀順序的 HTML。

PDF 沒有可靠的語意結構，以上皆為啟發式；掃描影像 PDF（無文字層）會提示需 OCR。
"""

from __future__ import annotations

from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException
from .._html_builder import escape, table
from .._stream_info import StreamInfo

_PDF_EXT = ".pdf"
_PDF_MIME = "application/pdf"

# 啟發式參數
_HEADING_MIN_SIZE = 13.0   # 字級大於此值的單行才可能是標題
_HEADING_MAX_LEN = 120     # 標題不會太長
_LINE_TOLERANCE = 3.0      # 同一行的詞 top 差異容忍值（px）


class PdfConverter(DocumentConverter):
    priority = 5.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        if ext == _PDF_EXT or mime == _PDF_MIME:
            return True
        # 偷看魔術位元組 %PDF
        pos = file_stream.tell()
        head = file_stream.read(5)
        file_stream.seek(pos)
        return head[:4] == b"%PDF"

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        try:
            import pdfplumber  # noqa: PLC0415
        except ImportError as exc:
            raise MissingDependencyException(
                "PdfConverter 需要 pdfplumber，請執行："
                "pip install 'doc2html[pdf]'"
            ) from exc

        parts: list[str] = []
        title: str | None = None
        had_content = False

        with pdfplumber.open(file_stream) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                items, page_title = self._page_items(page)
                if page_title and title is None:
                    title = page_title
                parts.append(f'<section class="page" id="page-{page_no}">')
                for _top, html in items:
                    parts.append(html)
                    had_content = True
                parts.append("</section>")

        if not had_content:
            parts.append(
                "<p><em>（未抽取到文字，可能是掃描影像 PDF，"
                "需要 OCR 才能處理）</em></p>"
            )

        return DocumentConverterResult(
            "\n".join(parts), title=title or stream_info.filename
        )

    def _page_items(self, page):
        """回傳 (依 top 排序的 [(top, html)], 本頁推測標題)。"""
        tables = page.find_tables()
        table_bboxes = [t.bbox for t in tables]  # (x0, top, x1, bottom)

        items: list[tuple[float, str]] = []
        for t in tables:
            data = [
                ["" if c is None else str(c).strip() for c in row]
                for row in t.extract()
            ]
            if not data:
                continue
            header, *body = data
            items.append((t.bbox[1], table(body, header=header)))

        # 文字：過濾掉落在表格框內的詞
        try:
            words = page.extract_words(extra_attrs=["size"])
        except Exception:
            words = page.extract_words()
        words = [w for w in words if not _inside_any(w, table_bboxes)]

        page_title = None
        for top, text, size in self._iter_blocks(words):
            if _is_heading(text, size):
                items.append((top, f"<h2>{escape(text)}</h2>"))
                if page_title is None:
                    page_title = text
            else:
                items.append((top, f"<p>{escape(text)}</p>"))

        items.sort(key=lambda it: it[0])
        return items, page_title

    def _iter_blocks(self, words):
        """把詞分行、再依垂直間距合併成段落。

        產出 (top, 合併文字, 代表字級)。標題行會自成一塊（不與內文合併）。
        """
        lines = _group_lines(words)

        buf: list[str] = []
        buf_top = 0.0
        prev_bottom = None

        for line in lines:
            text = " ".join(w["text"] for w in line).strip()
            if not text:
                continue
            line_top = min(w["top"] for w in line)
            line_bottom = max(w["bottom"] for w in line)
            size = max((w.get("size", 0.0) for w in line), default=0.0)
            line_height = max(line_bottom - line_top, 1.0)

            if _is_heading(text, size):
                if buf:
                    yield buf_top, " ".join(buf), 0.0
                    buf = []
                yield line_top, text, size
                prev_bottom = line_bottom
                continue

            # 與前一行間距過大 → 視為新段落
            gap = (line_top - prev_bottom) if prev_bottom is not None else 0.0
            if buf and gap > line_height * 0.8:
                yield buf_top, " ".join(buf), 0.0
                buf = []

            if not buf:
                buf_top = line_top
            buf.append(text)
            prev_bottom = line_bottom

        if buf:
            yield buf_top, " ".join(buf), 0.0


def _group_lines(words):
    """把詞依 top 分行（同行 top 差異在容忍值內）。"""
    words = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
    lines: list[list] = []
    current: list = []
    current_top = None
    for w in words:
        if current_top is None or abs(w["top"] - current_top) <= _LINE_TOLERANCE:
            if current_top is None:
                current_top = w["top"]
            current.append(w)
        else:
            lines.append(current)
            current = [w]
            current_top = w["top"]
    if current:
        lines.append(current)
    return lines


def _inside_any(word, bboxes) -> bool:
    """詞是否落在任一表格 bbox 內（給點容忍值）。"""
    cx = (word["x0"] + word["x1"]) / 2
    cy = (word["top"] + word["bottom"]) / 2
    for x0, top, x1, bottom in bboxes:
        if x0 - 1 <= cx <= x1 + 1 and top - 1 <= cy <= bottom + 1:
            return True
    return False


def _is_heading(text: str, size: float) -> bool:
    if size <= _HEADING_MIN_SIZE:
        return False
    if "\n" in text.strip():
        return False
    return len(text) <= _HEADING_MAX_LEN
