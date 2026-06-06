"""CSV / TSV 轉換器：轉成 HTML 表格。"""

from __future__ import annotations

import csv
import io
from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._html_builder import table
from .._stream_info import StreamInfo

_CSV_EXTENSIONS = {".csv", ".tsv"}
_CSV_MIMES = {"text/csv", "text/tab-separated-values", "application/csv"}


class CsvConverter(DocumentConverter):
    """把 CSV/TSV 第一列當表頭，其餘當資料列。"""

    priority = 5.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext in _CSV_EXTENSIONS or mime in _CSV_MIMES

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        charset = stream_info.charset or "utf-8"
        text = file_stream.read().decode(charset, errors="replace")

        # 用 csv.Sniffer 猜分隔符號，失敗就依副檔名退而求其次
        delimiter = "\t" if (stream_info.extension or "").lower() == ".tsv" else ","
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;|")
            delimiter = dialect.delimiter
        except csv.Error:
            pass

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not rows:
            return DocumentConverterResult(
                "<p><em>（空白 CSV）</em></p>", title=stream_info.filename
            )

        header, *body = rows
        return DocumentConverterResult(
            table(body, header=header), title=stream_info.filename
        )
