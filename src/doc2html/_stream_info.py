"""StreamInfo: 描述一份輸入資料的中介資訊（檔名、副檔名、MIME type 等）。

參考 MarkItDown 的設計：轉換器不直接看檔案路徑，而是看這份「線索」物件，
這樣同一套轉換器也能處理檔案、bytes、URL 串流等不同來源。
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, kw_only=True)
class StreamInfo:
    """描述一個位元組串流的所有已知線索（任一欄位都可能是 None）。"""

    mimetype: str | None = None
    extension: str | None = None  # 含點，例如 ".pdf"
    charset: str | None = None
    filename: str | None = None  # 僅檔名，例如 "report.pdf"
    local_path: str | None = None  # 完整本機路徑
    url: str | None = None  # 來源 URL（若有）

    def copy_and_update(self, **kwargs) -> StreamInfo:
        """回傳一份套用了新欄位的複本（不修改原物件）。"""
        return replace(self, **kwargs)
