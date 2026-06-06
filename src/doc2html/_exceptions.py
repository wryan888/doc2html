"""doc2html 的例外類型階層。"""

from __future__ import annotations


class Doc2HtmlException(Exception):
    """所有 doc2html 例外的基底類別。"""


class MissingDependencyException(Doc2HtmlException):
    """需要的第三方套件沒安裝時拋出（例如要轉 PDF 卻沒裝 pdfplumber）。"""


class UnsupportedFormatException(Doc2HtmlException):
    """找不到任何能處理這個輸入的轉換器時拋出。"""


class FailedConversionAttempt:
    """記錄某個轉換器嘗試失敗的細節，方便彙整錯誤訊息。"""

    def __init__(self, converter, exc_info=None):
        self.converter = converter
        self.exc_info = exc_info


class FileConversionException(Doc2HtmlException):
    """所有「有匹配到轉換器、但每個都失敗」的情況。"""

    def __init__(
        self,
        message: str | None = None,
        attempts: list[FailedConversionAttempt] | None = None,
    ):
        self.attempts = attempts or []
        if message is None:
            if self.attempts:
                lines = ["所有匹配的轉換器都失敗了："]
                for a in self.attempts:
                    name = type(a.converter).__name__
                    reason = "(未知錯誤)"
                    if a.exc_info and a.exc_info[1] is not None:
                        exc = a.exc_info[1]
                        reason = f"{type(exc).__name__}: {exc}"
                    lines.append(f"  - {name}: {reason}")
                message = "\n".join(lines)
            else:
                message = "所有匹配的轉換器都失敗了。"
        super().__init__(message)
