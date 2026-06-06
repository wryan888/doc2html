"""HTML 輸入轉換器：清理既有 HTML，抽出主要內容後重新輸出乾淨片段。

輸入已經是 HTML，所以重點不是「轉成 HTML」，而是「正規化」：
去掉 script/style/註解等雜訊，抽出 <body>（或 <article>/<main>）內容與標題。
若沒裝 beautifulsoup4，就退化為粗略的字串處理。
"""

from __future__ import annotations

import re
from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo

_HTML_EXTENSIONS = {".html", ".htm", ".xhtml"}
_HTML_MIMES = {"text/html", "application/xhtml+xml"}


class HtmlConverter(DocumentConverter):
    priority = 5.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext in _HTML_EXTENSIONS or mime in _HTML_MIMES

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        charset = stream_info.charset or "utf-8"
        text = file_stream.read().decode(charset, errors="replace")
        try:
            return self._convert_with_bs4(text, stream_info)
        except ImportError:
            return self._convert_fallback(text, stream_info)

    def _convert_with_bs4(self, text, stream_info):
        from bs4 import BeautifulSoup  # noqa: PLC0415

        soup = BeautifulSoup(text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else None

        # 移除非內容元素
        for tag in soup(["script", "style", "noscript", "template", "head"]):
            tag.decompose()

        # 優先取語意主體
        root = (
            soup.find("article")
            or soup.find("main")
            or soup.body
            or soup
        )
        body_html = root.decode_contents() if root else ""
        return DocumentConverterResult(
            body_html.strip(), title=title or stream_info.filename
        )

    def _convert_fallback(self, text, stream_info):
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL
        )
        title = None
        if title_match:
            # 與 bs4 路徑一致：title 取純文字，去掉任何內嵌標籤
            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() or None

        # 粗略剝掉 script/style 與 head
        text = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL
        )
        body_match = re.search(
            r"<body[^>]*>(.*?)</body>", text, re.IGNORECASE | re.DOTALL
        )
        body_html = body_match.group(1) if body_match else text
        return DocumentConverterResult(
            body_html.strip(), title=title or stream_info.filename
        )
