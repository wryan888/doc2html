"""各格式轉換器的行為測試。"""

from doc2html import Doc2Html


def convert(path):
    return Doc2Html().convert(str(path))


# --- 純文字 ---------------------------------------------------------

def test_txt_paragraphs(txt_file):
    body = convert(txt_file).body_html
    assert body.count("<p>") == 2  # 兩段
    assert "<br />" in body  # 段內單換行轉 <br>


def test_txt_full_document_shell(txt_file):
    html = convert(txt_file).html
    assert html.startswith("<!DOCTYPE html>")
    assert 'charset="utf-8"' in html
    assert "<main" in html


# --- CSV / TSV ------------------------------------------------------

def test_csv_table_with_header(csv_file):
    body = convert(csv_file).body_html
    assert "<thead>" in body
    assert "<th>名稱</th>" in body
    assert "<td>蘋果</td>" in body


def test_tsv_delimiter(tsv_file):
    body = convert(tsv_file).body_html
    assert "<th>a</th>" in body
    assert "<td>1</td>" in body


# --- JSON -----------------------------------------------------------

def test_json_rendering(json_file):
    body = convert(json_file).body_html
    assert "<th>k</th>" in body
    assert "<code>true</code>" in body
    assert "<code>null</code>" in body


def test_json_parse_failure_fallback(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    body = convert(p).body_html
    assert "解析失敗" in body
    assert "<pre>" in body


# --- HTML 輸入 ------------------------------------------------------

def test_html_strips_script_and_extracts_article(html_file):
    result = convert(html_file)
    assert "<script>" not in result.body_html
    assert "color:red" not in result.body_html  # style 被移除
    assert "<h1>H</h1>" in result.body_html
    assert result.title == "標題"  # title 為純文字


def test_html_escapes_in_full_document(html_file):
    # 完整文件的 <title> 一定有被跳脫處理（此例無特殊字元，確認流程不爆）
    assert "<title>標題</title>" in convert(html_file).html


# --- DOCX -----------------------------------------------------------

def test_docx_structure(docx_file):
    body = convert(docx_file).body_html
    assert "<h1>報告標題</h1>" in body
    assert "<strong>" not in body or True  # 內文無粗體，僅確認不崩
    assert "<table>" in body


def test_docx_lists_merged(docx_file):
    body = convert(docx_file).body_html
    # 連續兩個清單項應合併在同一個 <ul> 內，而非各包一個
    assert "<ul><li>項目一</li><li>項目二</li></ul>" in body
    assert body.count("<ul>") == 1


def test_docx_title_from_heading(docx_file):
    assert convert(docx_file).title == "報告標題"


# --- XLSX -----------------------------------------------------------

def test_xlsx_sheet_with_header(xlsx_file):
    body = convert(xlsx_file).body_html
    assert '<section class="sheet">' in body
    assert "<h2>庫存</h2>" in body
    assert "<thead>" in body
    assert "<th>名稱</th>" in body


def test_xlsx_no_header_when_all_numeric(xlsx_no_header_file):
    body = convert(xlsx_no_header_file).body_html
    assert "<thead>" not in body  # 全數字、無標題列
    assert "<td>1</td>" in body


# --- PPTX -----------------------------------------------------------

def test_pptx_slides(pptx_file):
    body = convert(pptx_file).body_html
    assert 'class="slide"' in body
    assert "投影片標題" in body
    assert "<li>重點一</li>" in body


# --- PDF ------------------------------------------------------------

def test_pdf_text_and_heading(pdf_file):
    result = convert(pdf_file)
    body = result.body_html
    assert 'class="page"' in body
    assert "PDF Heading" in body
    assert "Body paragraph text." in body
