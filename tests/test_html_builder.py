"""公開 HTML 組裝 API（doc2html.html）的行為測試。"""

from doc2html import html


def test_escape_handles_none_and_quotes():
    assert html.escape(None) == ""
    assert html.escape('a & "b" <c>') == "a &amp; &quot;b&quot; &lt;c&gt;"


def test_tag_builds_attrs_and_strips_trailing_underscore():
    out = html.tag("div", "hi", class_="line", data_id=3)
    assert out == '<div class="line" data-id="3">hi</div>'


def test_document_default_css_and_shell():
    doc = html.document("<p>hi</p>", title="標題")
    assert doc.startswith("<!DOCTYPE html>")
    assert "<title>標題</title>" in doc
    assert "main.doc2html" in doc  # 內建預設樣式
    assert "<p>hi</p>" in doc


def test_document_custom_css_override():
    css = "body{background:#000}"
    doc = html.document("<p>hi</p>", title="x", css=css)
    assert "body{background:#000}" in doc
    assert "main.doc2html" not in doc  # 預設樣式已被整組覆寫


def test_document_lang_override():
    doc = html.document("x", lang="en")
    assert '<html lang="en">' in doc
