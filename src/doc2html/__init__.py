"""doc2html — 把各種文件格式轉成 HTML（靈感來自 microsoft/markitdown）。"""

from . import html
from ._base_converter import DocumentConverter, DocumentConverterResult
from ._doc2html import ConvertedDocument, Doc2Html
from ._exceptions import (
    Doc2HtmlException,
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)
from ._stream_info import StreamInfo
from .ocr import GeminiOcr, OcrBackend

__version__ = "0.5.0"

__all__ = [
    "html",
    "Doc2Html",
    "ConvertedDocument",
    "DocumentConverter",
    "DocumentConverterResult",
    "StreamInfo",
    "OcrBackend",
    "GeminiOcr",
    "Doc2HtmlException",
    "MissingDependencyException",
    "UnsupportedFormatException",
    "FileConversionException",
    "__version__",
]
