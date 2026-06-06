"""OCR 後備與 Gemini 後端的測試（不打真 API）。"""

import pytest

from doc2html import Doc2Html
from doc2html.ocr import GeminiOcr, _strip_code_fence


class FakeOcr:
    """測試用 OCR 後端：記錄呼叫、回傳固定 HTML。"""

    def __init__(self, html="<p>OCR 辨識文字</p>"):
        self.html = html
        self.calls = []

    def image_to_html(self, image_png, *, lang="auto"):
        self.calls.append((image_png, lang))
        return self.html


def convert(path, **kwargs):
    return Doc2Html(**kwargs).convert(str(path))


# --- PDF OCR 後備 ---------------------------------------------------

def test_pdf_ocr_fallback_invoked(pdf_scanned_file):
    pytest.importorskip("pypdfium2")
    fake = FakeOcr()
    body = convert(pdf_scanned_file, ocr=fake).body_html
    assert "OCR 辨識文字" in body
    assert len(fake.calls) == 1  # 一頁 rasterize 並呼叫一次
    assert isinstance(fake.calls[0][0], bytes) and fake.calls[0][0][:4] == b"\x89PNG"


def test_pdf_without_ocr_shows_hint(pdf_scanned_file):
    body = convert(pdf_scanned_file).body_html
    assert "OCR" in body  # 未設定後端 → 提示需要 OCR


def test_pdf_with_text_skips_ocr(pdf_file):
    pytest.importorskip("pypdfium2")
    fake = FakeOcr()
    body = convert(pdf_file, ocr=fake).body_html
    assert "PDF Heading" in body
    assert fake.calls == []  # 有文字層就不應呼叫 OCR


# --- GeminiOcr（注入 fake client，不需 google-genai）---------------

class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, text):
        self._text = text
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResp(self._text)


class _FakeClient:
    def __init__(self, text):
        self.models = _FakeModels(text)


def test_gemini_strips_code_fence():
    client = _FakeClient("```html\n<h1>標題</h1>\n```")
    ocr = GeminiOcr(client=client, model="gemini-2.5-flash")
    assert ocr.image_to_html(b"\x89PNG...") == "<h1>標題</h1>"
    # 圖片有確實帶進 contents
    contents = client.models.last_kwargs["contents"]
    assert contents[1]["inline_data"]["mime_type"] == "image/png"


def test_gemini_plain_html_passthrough():
    client = _FakeClient("<p>純文字</p>")
    assert GeminiOcr(client=client).image_to_html(b"x") == "<p>純文字</p>"


def test_gemini_missing_api_key(monkeypatch):
    from doc2html import Doc2HtmlException

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # client 為 None 且無金鑰 → 取用時報錯（不需安裝 google-genai 也能測，
    # 因為缺金鑰的檢查在嘗試建立 client 前；若無 SDK 會先報缺依賴，故兩者皆可）
    with pytest.raises(Doc2HtmlException):
        GeminiOcr().image_to_html(b"x")


# --- 純函式 ---------------------------------------------------------

def test_strip_code_fence_variants():
    assert _strip_code_fence("```html\n<p>a</p>\n```") == "<p>a</p>"
    assert _strip_code_fence("```\n<p>b</p>\n```") == "<p>b</p>"
    assert _strip_code_fence("<p>c</p>") == "<p>c</p>"
    assert _strip_code_fence("  <p>d</p>  ") == "<p>d</p>"
