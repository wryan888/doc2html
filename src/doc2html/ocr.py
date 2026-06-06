"""OCR 後端：把掃描頁面的圖片轉成 HTML。

設計成可插拔介面（OcrBackend），讓 provider 的選擇權在使用者手上：
內建 GeminiOcr（雲端、品質導向），日後可再加 Tesseract（本地）或其他
vision LLM，介面一致即可互換。

預設情況下 doc2html 不啟用任何 OCR；要用時需明確傳入後端，例如：

    from doc2html import Doc2Html
    from doc2html.ocr import GeminiOcr

    engine = Doc2Html(ocr=GeminiOcr())   # 讀取 GEMINI_API_KEY 環境變數
    print(engine.convert("scanned.pdf").html)
"""

from __future__ import annotations

import os
import re
from typing import Protocol, runtime_checkable

from ._exceptions import Doc2HtmlException, MissingDependencyException


@runtime_checkable
class OcrBackend(Protocol):
    """OCR 後端介面：把一張頁面圖片（PNG bytes）轉成 HTML 片段。"""

    def image_to_html(self, image_png: bytes, *, lang: str = "auto") -> str:
        ...


# 給 vision LLM 的指示：忠實轉錄、輸出乾淨片段、明確禁止捏造（降低幻覺風險）。
_OCR_PROMPT = """\
你是精準的 OCR 引擎。請把這張文件頁面圖片的內容轉成乾淨、語意化的 HTML 片段。

規則：
- 只輸出會放進 <main> 的 HTML 片段，不要 <html>/<head>/<body>，也不要 ``` 圍欄。
- 保留結構：標題用 <h1>~<h6>，段落用 <p>，清單用 <ul>/<ol>，表格用 <table>。
- 忠實轉錄，不要翻譯、不要改寫、不要新增原圖沒有的內容。
- 看不清楚的字保留原樣或留空，絕對不要猜測或捏造文字。
- 若頁面空白或無可辨識文字，回傳空字串。
"""


class GeminiOcr:
    """用 Google Gemini 的 vision 能力做頁面 OCR → HTML。

    需要 `pip install 'doc2html[ocr-gemini]'`，並提供 API 金鑰
    （參數 api_key，或環境變數 GEMINI_API_KEY）。
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
        client=None,
    ):
        self._api_key = api_key
        self._model = model
        self._client = client  # 可注入，方便測試（不打真 API）

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from google import genai  # noqa: PLC0415
        except ImportError as exc:
            raise MissingDependencyException(
                "GeminiOcr 需要 google-genai，請執行："
                "pip install 'doc2html[ocr-gemini]'"
            ) from exc
        key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise Doc2HtmlException(
                "找不到 Gemini API 金鑰：請設定 GEMINI_API_KEY 環境變數，"
                "或在建立 GeminiOcr(api_key=...) 時傳入。"
            )
        self._client = genai.Client(api_key=key)
        return self._client

    def image_to_html(self, image_png: bytes, *, lang: str = "auto") -> str:
        client = self._get_client()
        # 用 dict 形式的 inline_data 傳圖片，避免硬綁 SDK 的 types 模組
        contents = [
            _OCR_PROMPT,
            {"inline_data": {"mime_type": "image/png", "data": image_png}},
        ]
        response = client.models.generate_content(
            model=self._model, contents=contents
        )
        text = getattr(response, "text", "") or ""
        return _strip_code_fence(text).strip()


def _strip_code_fence(text: str) -> str:
    """移除 LLM 可能多包的 ```html ... ``` 圍欄。"""
    stripped = text.strip()
    fence = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", stripped, re.DOTALL)
    if fence:
        return fence.group(1)
    return stripped
