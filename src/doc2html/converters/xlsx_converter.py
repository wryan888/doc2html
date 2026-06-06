"""Excel (.xlsx) 轉換器：每個工作表轉成一個帶標題的 HTML 表格。"""

from __future__ import annotations

from typing import BinaryIO

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException
from .._html_builder import escape, table
from .._stream_info import StreamInfo

_XLSX_EXT = {".xlsx", ".xlsm"}
_XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class XlsxConverter(DocumentConverter):
    priority = 5.0

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext in _XLSX_EXT or mime == _XLSX_MIME

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo
    ) -> DocumentConverterResult:
        try:
            import openpyxl  # noqa: PLC0415
        except ImportError as exc:
            raise MissingDependencyException(
                "XlsxConverter 需要 openpyxl，請執行："
                "pip install 'doc2html[xlsx]'"
            ) from exc

        # data_only=True：取算好的值而非公式字串
        wb = openpyxl.load_workbook(file_stream, data_only=True, read_only=True)
        parts: list[str] = []
        for ws in wb.worksheets:
            raw_rows = list(ws.iter_rows(values_only=True))
            rows = [[_fmt(cell) for cell in row] for row in raw_rows]
            # 去掉尾端整列空白
            while rows and all(c == "" for c in rows[-1]):
                rows.pop()
                raw_rows.pop()

            section = ['<section class="sheet">']
            section.append(f"<h2>{escape(ws.title)}</h2>")
            if not rows:
                section.append("<p><em>（空白工作表）</em></p>")
            elif _looks_like_header(raw_rows):
                header, *body = rows
                section.append(table(body, header=header))
            else:
                # 無明顯表頭：整片當資料列，不產生 <thead>
                section.append(table(rows))
            section.append("</section>")
            parts.append("\n".join(section))

        wb.close()
        return DocumentConverterResult(
            "\n".join(parts), title=stream_info.filename
        )


def _fmt(value) -> str:
    """把儲存格的值轉成乾淨字串。"""
    if value is None:
        return ""
    return str(value)


def _looks_like_header(raw_rows) -> bool:
    """啟發式判斷第一列是否為表頭。

    條件：至少要有一列資料列，且第一列每格皆非空、皆為文字（非數字/日期）。
    這能擋掉「整張都是數字資料、沒有標題列」被誤判成表頭的情況。
    """
    if len(raw_rows) < 2:
        return False  # 只有一列（或空），當純資料看待
    first = raw_rows[0]
    if not first or any(cell is None or str(cell).strip() == "" for cell in first):
        return False
    return all(isinstance(cell, str) for cell in first)
