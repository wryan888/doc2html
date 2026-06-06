"""分派邏輯、註冊表、錯誤處理的測試。"""

import io

import pytest

from doc2html import (
    Doc2Html,
    DocumentConverter,
    DocumentConverterResult,
    FileConversionException,
    StreamInfo,
    UnsupportedFormatException,
)
from doc2html._exceptions import FailedConversionAttempt

# --- 來源型別 -------------------------------------------------------

def test_convert_bytes_with_stream_info():
    r = Doc2Html().convert(b"a,b\n1,2", stream_info=StreamInfo(extension=".csv"))
    assert "<th>a</th>" in r.body_html


def test_convert_nonseekable_stream():
    class NonSeekable(io.RawIOBase):
        def __init__(self, data):
            self._d = data
        def readable(self):
            return True
        def seekable(self):
            return False
        def read(self, n=-1):
            d, self._d = self._d, b""
            return d

    r = Doc2Html().convert(
        NonSeekable(b"hello text"), stream_info=StreamInfo(extension=".txt")
    )
    assert "hello text" in r.body_html


# --- 標題覆寫 -------------------------------------------------------

def test_title_override(csv_file):
    r = Doc2Html().convert(str(csv_file), title="自訂標題")
    assert r.title == "自訂標題"
    assert "<title>自訂標題</title>" in r.html


# --- 兜底與優先序 ---------------------------------------------------

def test_unknown_text_falls_back_to_plaintext():
    r = Doc2Html().convert(b"just some text", stream_info=StreamInfo())
    assert "<p>just some text</p>" in r.body_html


def test_binary_unknown_raises_unsupported():
    with pytest.raises(UnsupportedFormatException):
        Doc2Html().convert(b"\x00\x01\x02\xff", stream_info=StreamInfo())


def test_custom_converter_priority_override():
    class Custom(DocumentConverter):
        priority = 100.0
        def accepts(self, file_stream, stream_info):
            return (stream_info.extension or "") == ".csv"
        def convert(self, file_stream, stream_info):
            return DocumentConverterResult("<p>custom</p>", title="custom")

    engine = Doc2Html()
    engine.register_converter(Custom())
    r = engine.convert(b"a,b\n1,2", stream_info=StreamInfo(extension=".csv"))
    assert r.body_html == "<p>custom</p>"  # 高優先序蓋過內建 CSV


# --- 錯誤訊息 -------------------------------------------------------

def test_file_conversion_exception_lists_reason():
    class Boom(DocumentConverter):
        priority = 50.0
        def accepts(self, file_stream, stream_info):
            return True
        def convert(self, file_stream, stream_info):
            raise ValueError("壞掉了")

    engine = Doc2Html(enable_builtins=False)
    engine.register_converter(Boom())
    with pytest.raises(FileConversionException) as exc:
        engine.convert(b"\x00binary", stream_info=StreamInfo())
    assert "Boom" in str(exc.value)
    assert "壞掉了" in str(exc.value)


def test_failed_attempt_carries_converter():
    boom = object()
    att = FailedConversionAttempt(boom)
    assert att.converter is boom


# --- accepts() 例外不應中斷分派 ------------------------------------

def test_accepts_exception_is_skipped(caplog):
    class BadAccepts(DocumentConverter):
        priority = 100.0
        def accepts(self, file_stream, stream_info):
            raise RuntimeError("accepts 爆了")
        def convert(self, file_stream, stream_info):
            return DocumentConverterResult("<p>x</p>")

    engine = Doc2Html()  # 仍有內建純文字兜底
    engine.register_converter(BadAccepts())
    r = engine.convert(b"plain", stream_info=StreamInfo(extension=".txt"))
    # BadAccepts 被跳過，純文字兜底接手
    assert "<p>plain</p>" in r.body_html
