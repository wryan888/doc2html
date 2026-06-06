"""共用 fixtures：在 tmp_path 動態產生各格式測試檔。

二進位格式（docx/xlsx/pptx/pdf）若缺對應套件就 skip 相關測試，
讓核心測試在零依賴環境也能跑。
"""

import json

import pytest


@pytest.fixture
def txt_file(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("第一段。\n同段第二行。\n\n第二段。", encoding="utf-8")
    return p


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "sample.csv"
    p.write_text("名稱,價格\n蘋果,30\n香蕉,15", encoding="utf-8")
    return p


@pytest.fixture
def tsv_file(tmp_path):
    p = tmp_path / "sample.tsv"
    p.write_text("a\tb\n1\t2", encoding="utf-8")
    return p


@pytest.fixture
def json_file(tmp_path):
    p = tmp_path / "sample.json"
    p.write_text(
        json.dumps(
            {"k": "v", "items": [1, 2], "ok": True, "n": None},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture
def html_file(tmp_path):
    p = tmp_path / "sample.html"
    p.write_text(
        "<html><head><title>標題</title><style>p{color:red}</style></head>"
        "<body><article><h1>H</h1><p>內文<script>x()</script></p>"
        "</article></body></html>",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def docx_file(tmp_path):
    docx = pytest.importorskip("docx")
    p = tmp_path / "sample.docx"
    d = docx.Document()
    d.add_heading("報告標題", level=1)
    d.add_paragraph("內文")
    d.add_paragraph("項目一", style="List Bullet")
    d.add_paragraph("項目二", style="List Bullet")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "A"
    t.cell(0, 1).text = "B"
    t.cell(1, 0).text = "1"
    t.cell(1, 1).text = "2"
    d.save(p)
    return p


@pytest.fixture
def xlsx_file(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    p = tmp_path / "sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "庫存"
    ws.append(["名稱", "價格"])
    ws.append(["蘋果", 30])
    wb.save(p)
    return p


@pytest.fixture
def xlsx_no_header_file(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    p = tmp_path / "nohdr.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([1, 2, 3])
    ws.append([4, 5, 6])
    wb.save(p)
    return p


@pytest.fixture
def pptx_file(tmp_path):
    pptx = pytest.importorskip("pptx")
    p = tmp_path / "sample.pptx"
    prs = pptx.Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "投影片標題"
    s.placeholders[1].text = "重點一\n重點二"
    prs.save(p)
    return p


@pytest.fixture
def pdf_file(tmp_path):
    pytest.importorskip("reportlab")
    pytest.importorskip("pdfminer")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    p = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(p), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "PDF Heading")
    c.setFont("Helvetica", 11)
    c.drawString(72, 690, "Body paragraph text.")
    c.save()
    return p
