"""PDF 轉換器：用 pdfminer.six 抽取文字，依版面分段成 HTML。

PDF 沒有可靠的語意結構，所以策略是：逐頁抽取文字區塊（text box），
每塊轉成一個段落，並用簡單的字級啟發式把「明顯偏大的單行」當成標題。
"""

from __future__ import annotations

from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException
from .._html_builder import escape
from .._stream_info import StreamInfo

_PDF_EXT = ".pdf"
_PDF_MIME = "application/pdf"


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
            from pdfminer.high_level import extract_pages  # noqa: PLC0415
            from pdfminer.layout import LTTextContainer, LTTextLine  # noqa: PLC0415
        except ImportError as exc:
            raise MissingDependencyException(
                "PdfConverter 需要 pdfminer.six，請執行："
                "pip install 'doc2html[pdf]'"
            ) from exc

        parts: list[str] = []
        title: str | None = None

        for page_no, page_layout in enumerate(extract_pages(file_stream), start=1):
            parts.append(f'<section class="page" id="page-{page_no}">')
            for element in page_layout:
                if not isinstance(element, LTTextContainer):
                    continue
                text = element.get_text().strip()
                if not text:
                    continue
                size = _avg_font_size(element, LTTextLine)
                is_heading = _looks_like_heading(text, size)
                if is_heading:
                    parts.append(f"<h2>{escape(text)}</h2>")
                    if title is None:
                        title = text
                else:
                    # 區塊內的軟換行以空白接合，段落本身成一個 <p>
                    joined = " ".join(
                        line.strip() for line in text.splitlines() if line.strip()
                    )
                    parts.append(f"<p>{escape(joined)}</p>")
            parts.append("</section>")

        if not any("<p>" in p or "<h2>" in p for p in parts):
            parts.append(
                "<p><em>（未抽取到文字，可能是掃描影像 PDF，"
                "需要 OCR 才能處理）</em></p>"
            )

        return DocumentConverterResult(
            "\n".join(parts), title=title or stream_info.filename
        )


def _avg_font_size(element, LTTextLine) -> float:
    sizes = []
    for line in element:
        if isinstance(line, LTTextLine):
            for char in line:
                size = getattr(char, "size", None)
                if size:
                    sizes.append(size)
    return sum(sizes) / len(sizes) if sizes else 0.0


def _looks_like_heading(text: str, size: float) -> bool:
    # 啟發式：字大（>13pt）、單行、且不太長，視為標題
    if size <= 13.0:
        return False
    if "\n" in text.strip():
        return False
    return len(text) <= 120
