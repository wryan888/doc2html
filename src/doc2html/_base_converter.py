"""轉換器的基底類別與轉換結果物件。"""

from __future__ import annotations

from typing import BinaryIO

from ._stream_info import StreamInfo


class DocumentConverterResult:
    """單一轉換的結果：HTML body 片段 + 可選標題。

    `body_html` 只是 <main> 內的片段；要拿可獨立開啟的整份文件，
    請用 Doc2Html 回傳的 `.html`（會套用文件模板）。
    """

    def __init__(self, body_html: str, *, title: str | None = None):
        self.body_html = body_html
        self.title = title

    def __str__(self) -> str:
        return self.body_html


class DocumentConverter:
    """所有轉換器的基底。子類別需實作 accepts() 與 convert()。"""

    # 數字越大越先嘗試。指定特定副檔名的轉換器用較高優先序，
    # 像「純文字」這種兜底的用較低優先序。
    priority: float = 0.0

    def __init__(
        self,
        *,
        embed_images: bool = True,
        max_image_bytes: int = 2_000_000,
        **_ignored,
    ):
        """共用選項：

        embed_images   是否把文件內的圖片以 base64 data URI 內嵌（預設 True）。
        max_image_bytes 單張圖片超過此大小（位元組）就退化為文字佔位，避免輸出爆量。
        不在意這些選項的轉換器（CSV、JSON…）直接忽略即可。
        """
        self.embed_images = embed_images
        self.max_image_bytes = max_image_bytes

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        """這個轉換器能不能處理這份輸入？

        實作時可看 stream_info 的副檔名/MIME，必要時也可偷看串流開頭，
        但看完務必把指標 seek 回原位（呼叫端會負責整體 seek，但偷看者要自理）。
        """
        raise NotImplementedError

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        """把串流轉成 HTML 片段。"""
        raise NotImplementedError
