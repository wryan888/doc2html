"""Doc2Html 主類別：管理轉換器註冊表，並把各種輸入分派給對的轉換器。"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
import sys
from dataclasses import dataclass
from typing import BinaryIO

from ._base_converter import DocumentConverter, DocumentConverterResult
from ._exceptions import (
    FailedConversionAttempt,
    FileConversionException,
    UnsupportedFormatException,
)
from ._html_builder import document
from ._stream_info import StreamInfo
from .converters import (
    CsvConverter,
    DocxConverter,
    HtmlConverter,
    JsonConverter,
    PdfConverter,
    PlainTextConverter,
    PptxConverter,
    XlsxConverter,
)

logger = logging.getLogger("doc2html")

# 註冊順序：實際嘗試時會再依 priority 由高到低排序，
# priority 相同者「後註冊的先試」（讓使用者自訂的轉換器能蓋過內建）。
_BUILTIN_CONVERTERS = [
    PlainTextConverter,  # 兜底，priority 最低
    CsvConverter,
    JsonConverter,
    HtmlConverter,
    DocxConverter,
    XlsxConverter,
    PptxConverter,
    PdfConverter,
]


@dataclass
class _Registration:
    converter: DocumentConverter
    order: int  # 註冊序號，用於穩定排序時的 tie-break


class Doc2Html:
    """把多種文件格式轉成 HTML 的主要進入點。

    用法：
        from doc2html import Doc2Html
        result = Doc2Html().convert("report.pdf")
        print(result.html)           # 完整可開啟的 HTML
        open("out.html", "w").write(result.html)
    """

    def __init__(
        self,
        *,
        enable_builtins: bool = True,
        embed_images: bool = True,
        max_image_bytes: int = 2_000_000,
    ):
        self._registrations: list[_Registration] = []
        self._counter = 0
        if enable_builtins:
            opts = {
                "embed_images": embed_images,
                "max_image_bytes": max_image_bytes,
            }
            for cls in _BUILTIN_CONVERTERS:
                self.register_converter(cls(**opts))

    # ---- 轉換器註冊 -------------------------------------------------

    def register_converter(self, converter: DocumentConverter) -> None:
        """加入一個轉換器（後註冊者在同優先序中優先）。"""
        self._registrations.append(_Registration(converter, self._counter))
        self._counter += 1

    def _ordered_converters(self) -> list[DocumentConverter]:
        # priority 高的先；同 priority 時 order 大的（後註冊）先
        ordered = sorted(
            self._registrations,
            key=lambda r: (r.converter.priority, r.order),
            reverse=True,
        )
        return [r.converter for r in ordered]

    # ---- 對外的 convert API ----------------------------------------

    def convert(
        self,
        source: str | os.PathLike | bytes | BinaryIO,
        *,
        stream_info: StreamInfo | None = None,
        title: str | None = None,
    ) -> ConvertedDocument:
        """轉換一份輸入。source 可為路徑、bytes 或已開啟的二進位串流。

        回傳的 ConvertedDocument 同時提供 `.html`（完整文件）與
        `.body_html`（僅片段），呼叫端可自行取用，毋需事先指定。
        """
        if isinstance(source, (str, os.PathLike)) and _looks_like_path(source):
            return self.convert_local(
                source, stream_info=stream_info, title=title
            )
        if isinstance(source, bytes):
            return self.convert_stream(
                io.BytesIO(source), stream_info=stream_info, title=title
            )
        # 視為已開啟的二進位串流
        return self.convert_stream(source, stream_info=stream_info, title=title)

    def convert_local(
        self,
        path: str | os.PathLike,
        *,
        stream_info: StreamInfo | None = None,
        title: str | None = None,
    ) -> ConvertedDocument:
        path = os.fspath(path)
        base = _guess_stream_info(path)
        if stream_info is not None:
            base = base.copy_and_update(
                **{k: v for k, v in vars(stream_info).items() if v is not None}
            )
        with open(path, "rb") as fh:
            return self.convert_stream(fh, stream_info=base, title=title)

    def convert_stream(
        self,
        file_stream: BinaryIO,
        *,
        stream_info: StreamInfo | None = None,
        title: str | None = None,
    ) -> ConvertedDocument:
        # 確保串流可重複 seek（accepts() 需要偷看開頭）
        if not file_stream.seekable():
            file_stream = io.BytesIO(file_stream.read())
        info = stream_info or StreamInfo()

        attempts: list[FailedConversionAttempt] = []
        for converter in self._ordered_converters():
            file_stream.seek(0)
            try:
                if not converter.accepts(file_stream, info):
                    continue
            except Exception:  # accepts 不該炸，炸了就跳過——但記下來方便除錯
                logger.debug(
                    "%s.accepts() 拋出例外，已跳過此轉換器",
                    type(converter).__name__,
                    exc_info=True,
                )
                continue

            file_stream.seek(0)
            try:
                result = converter.convert(file_stream, info)
            except Exception:
                attempts.append(
                    FailedConversionAttempt(converter, sys.exc_info())
                )
                continue
            return ConvertedDocument(
                result, override_title=title, source_info=info
            )

        if attempts:
            raise FileConversionException(attempts=attempts)
        raise UnsupportedFormatException(
            f"找不到能處理這份輸入的轉換器（"
            f"副檔名={info.extension!r}, mime={info.mimetype!r}）。"
        )


class ConvertedDocument:
    """包裝單次轉換結果，提供 body 片段與完整 HTML 文件兩種輸出。"""

    def __init__(
        self,
        result: DocumentConverterResult,
        *,
        override_title: str | None = None,
        source_info: StreamInfo | None = None,
    ):
        self._result = result
        self._override_title = override_title
        self._source_info = source_info

    @property
    def title(self) -> str | None:
        return self._override_title or self._result.title

    @property
    def body_html(self) -> str:
        """只含 <main> 內的 HTML 片段。"""
        return self._result.body_html

    @property
    def html(self) -> str:
        """完整、可獨立開啟的 HTML 文件。"""
        return document(self._result.body_html, title=self.title)

    # 直接 print(result) 時給出完整文件
    def __str__(self) -> str:
        return self.html


# ---- 模組層小工具 --------------------------------------------------


def _looks_like_path(source) -> bool:
    try:
        return os.path.exists(os.fspath(source))
    except (TypeError, ValueError):
        return False


def _guess_stream_info(path: str) -> StreamInfo:
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower() or None
    mime, _ = mimetypes.guess_type(path)
    return StreamInfo(
        filename=filename,
        extension=ext,
        mimetype=mime,
        local_path=path,
    )
