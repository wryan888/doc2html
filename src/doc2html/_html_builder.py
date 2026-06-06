"""產生 HTML 的小工具：跳脫、標籤、表格、完整文件模板。

所有轉換器都用這裡的函式來組 HTML，確保跳脫一致、輸出風格統一。
"""

from __future__ import annotations

import base64
from collections.abc import Iterable, Sequence
from html import escape as _escape


def escape(text: object) -> str:
    """跳脫文字內容（含引號），把 None 視為空字串。"""
    if text is None:
        return ""
    return _escape(str(text), quote=True)


def tag(name: str, content: str = "", **attrs) -> str:
    """組一個一般標籤，例如 tag('a', '連結', href='...')。

    屬性名稱結尾的底線會被去掉（class_ -> class）。
    """
    attr_str = _attrs_to_str(attrs)
    return f"<{name}{attr_str}>{content}</{name}>"


def void_tag(name: str, **attrs) -> str:
    """組一個自閉合標籤，例如 void_tag('img', src='...')。"""
    return f"<{name}{_attrs_to_str(attrs)} />"


def _attrs_to_str(attrs: dict) -> str:
    parts = []
    for key, value in attrs.items():
        if value is None or value is False:
            continue
        key = key.rstrip("_").replace("_", "-")
        if value is True:
            parts.append(f" {key}")
        else:
            parts.append(f' {key}="{escape(value)}"')
    return "".join(parts)


def image_data_uri(blob: bytes, content_type: str, alt: str = "") -> str:
    """把圖片位元組組成 <img>，src 為 base64 data URI。"""
    b64 = base64.b64encode(blob).decode("ascii")
    src = f"data:{content_type};base64,{b64}"
    return void_tag("img", src=src, alt=alt)


def paragraphs(text: str) -> str:
    """把多行純文字依空行切成 <p>，單一換行轉成 <br>。"""
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n")]
    out = []
    for block in blocks:
        if not block:
            continue
        inner = "<br />".join(escape(line) for line in block.split("\n"))
        out.append(f"<p>{inner}</p>")
    return "\n".join(out)


def table(
    rows: Iterable[Sequence[object]],
    header: Sequence[object] | None = None,
    caption: str | None = None,
) -> str:
    """把二維資料組成 <table>。header 為選用的表頭列。"""
    parts = ["<table>"]
    if caption:
        parts.append(f"<caption>{escape(caption)}</caption>")
    if header is not None:
        cells = "".join(f"<th>{escape(c)}</th>" for c in header)
        parts.append(f"<thead><tr>{cells}</tr></thead>")
    parts.append("<tbody>")
    for row in rows:
        cells = "".join(f"<td>{escape(c)}</td>" for c in row)
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


# 完整 HTML 文件的模板，附最低限度但好看的內建樣式。
_DOCUMENT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="generator" content="doc2html" />
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<main class="doc2html">
{body}
</main>
</body>
</html>
"""

_DEFAULT_CSS = """
:root { color-scheme: light dark; }
body { margin: 0; padding: 2rem; font-family: -apple-system, "Segoe UI",
  "PingFang TC", "Microsoft JhengHei", system-ui, sans-serif;
  line-height: 1.6; }
main.doc2html { max-width: 860px; margin: 0 auto; }
h1, h2, h3, h4, h5, h6 { line-height: 1.25; margin: 1.4em 0 0.5em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #bbb; padding: 0.4em 0.6em; text-align: left;
  vertical-align: top; }
thead th { background: rgba(127,127,127,0.15); }
caption { caption-side: top; font-weight: 600; text-align: left;
  margin-bottom: 0.4em; }
pre { background: rgba(127,127,127,0.12); padding: 1em; overflow-x: auto;
  border-radius: 6px; }
code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
img { max-width: 100%; height: auto; }
.slide { border-top: 2px solid rgba(127,127,127,0.4); padding-top: 1em;
  margin-top: 2em; }
.sheet { margin: 2em 0; }
blockquote { border-left: 4px solid rgba(127,127,127,0.4);
  margin: 1em 0; padding: 0.2em 1em; color: inherit; opacity: 0.85; }
"""


def document(
    body: str,
    title: str | None = None,
    lang: str = "zh-Hant",
    css: str | None = None,
) -> str:
    """把 body 片段包成一份完整、可獨立開啟的 HTML 文件。

    css 為 None 時用內建預設樣式；傳入字串可整組覆寫（例如深色主題）。
    """
    return _DOCUMENT_TEMPLATE.format(
        lang=escape(lang),
        title=escape(title or "Untitled Document"),
        css=_DEFAULT_CSS if css is None else css,
        body=body.strip(),
    )
