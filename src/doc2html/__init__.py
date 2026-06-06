"""doc2html — 把各種文件格式轉成 HTML（靈感來自 microsoft/markitdown）。"""

from ._base_converter import DocumentConverter, DocumentConverterResult
from ._doc2html import ConvertedDocument, Doc2Html
from ._exceptions import (
    Doc2HtmlException,
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)
from ._stream_info import StreamInfo

__version__ = "0.2.1"

__all__ = [
    "Doc2Html",
    "ConvertedDocument",
    "DocumentConverter",
    "DocumentConverterResult",
    "StreamInfo",
    "Doc2HtmlException",
    "MissingDependencyException",
    "UnsupportedFormatException",
    "FileConversionException",
    "__version__",
]
