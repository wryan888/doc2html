"""純文字轉換器（也是最後的兜底轉換器）。"""

from __future__ import annotations

from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._html_builder import paragraphs
from .._stream_info import StreamInfo

# 視為純文字的副檔名與 MIME
_TEXT_EXTENSIONS = {".txt", ".text", ".log", ".md", ".markdown", ".rst", ".tex"}


class PlainTextConverter(DocumentConverter):
    """把純文字轉成段落式 HTML。優先序很低，當作兜底。"""

    priority = -10.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        if ext in _TEXT_EXTENSIONS:
            return True
        if mime.startswith("text/"):
            return True
        # 兜底：嘗試解碼開頭，能解成文字就接受
        return self._looks_like_text(file_stream)

    def _looks_like_text(self, file_stream: BinaryIO) -> bool:
        pos = file_stream.tell()
        try:
            sample = file_stream.read(2048)
        finally:
            file_stream.seek(pos)
        if not sample:
            return True
        if b"\x00" in sample:
            return False
        try:
            sample.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        charset = stream_info.charset or "utf-8"
        raw = file_stream.read()
        try:
            text = raw.decode(charset, errors="replace")
        except (LookupError, TypeError):
            text = raw.decode("utf-8", errors="replace")
        return DocumentConverterResult(
            paragraphs(text), title=stream_info.filename
        )
