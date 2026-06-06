"""公開的 HTML 組裝工具。

把內部 `_html_builder` 的小工具公開出來，讓外部專案（例如 VSUB）能重用一致的
跳脫與文件模板，不必各自手刻 HTML。

範例::

    from doc2html import html

    body = html.tag("h1", html.escape(title))
    doc = html.document(body, title=title, css=my_dark_css)
"""

from __future__ import annotations

from ._html_builder import (
    document,
    escape,
    image_data_uri,
    paragraphs,
    table,
    tag,
    void_tag,
)

__all__ = [
    "escape",
    "tag",
    "void_tag",
    "image_data_uri",
    "paragraphs",
    "table",
    "document",
]
