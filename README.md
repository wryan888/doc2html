# doc2html

把多種文件格式轉成 **HTML** 的 Python 工具與函式庫，靈感與架構來自
[microsoft/markitdown](https://github.com/microsoft/markitdown)——差別在於
**輸出格式是 HTML 而非 Markdown**，並保留文件的結構（標題、清單、表格、連結）。

這是一個用來「學習文件處理能力」的專案：每個格式都有獨立的轉換器，
程式碼刻意寫得直白、好讀，方便對照各種檔案格式的內部結構是怎麼被讀出來的。

## 支援格式

| 格式 | 副檔名 | 依賴套件 |
|------|--------|----------|
| PDF | `.pdf` | `pdfminer.six` |
| Word | `.docx` | `python-docx` |
| Excel | `.xlsx` / `.xlsm` | `openpyxl` |
| PowerPoint | `.pptx` | `python-pptx` |
| HTML | `.html` / `.htm` | `beautifulsoup4`（選用，無則退化處理） |
| CSV / TSV | `.csv` / `.tsv` | 內建 |
| JSON | `.json` / `.jsonl` | 內建 |
| 純文字 | `.txt` / `.md` / … | 內建（也是兜底轉換器） |

## 安裝

```bash
pip install -e '.[all]'        # 安裝全部格式的依賴
pip install -e '.[pdf,docx]'   # 只裝需要的
pip install -e .               # 只要內建格式（CSV/JSON/純文字/HTML）
```

## 命令列用法

```bash
doc2html report.pdf > report.html        # 轉檔並導向輸出
doc2html data.xlsx -o data.html          # 指定輸出檔
cat notes.txt | doc2html --extension .txt   # 從 stdin 讀
doc2html page.html --fragment            # 只輸出 <main> 片段，不含完整外殼
doc2html slides.pptx --title "我的簡報"   # 覆寫 <title>
```

## Python API

```python
from doc2html import Doc2Html

engine = Doc2Html()
result = engine.convert("report.pdf")

print(result.title)        # 推測出的標題
print(result.html)         # 完整、可獨立開啟的 HTML 文件
print(result.body_html)    # 只含 <main> 內的 HTML 片段

with open("report.html", "w", encoding="utf-8") as fh:
    fh.write(result.html)
```

也可以直接餵 bytes 或已開啟的二進位串流：

```python
from doc2html import Doc2Html, StreamInfo

data = open("data.csv", "rb").read()
result = Doc2Html().convert(data, stream_info=StreamInfo(extension=".csv"))
```

## 架構（對照 markitdown）

```
Doc2Html                 主類別：管理轉換器註冊表、依優先序分派
 └─ DocumentConverter    每種格式一個轉換器，實作 accepts() / convert()
      └─ 回傳 HTML 片段 + 標題
 └─ _html_builder        共用的 HTML 跳脫、表格、文件模板工具
 └─ StreamInfo           描述輸入的線索（副檔名 / MIME / 檔名）
```

分派流程：

1. 依輸入推測 `StreamInfo`（副檔名、MIME）。
2. 轉換器依 `priority` 由高到低排序，逐一呼叫 `accepts()`。
3. 第一個接受的轉換器執行 `convert()`，回傳 HTML 片段。
4. 主類別把片段包進完整 HTML 文件模板（含 `<meta charset>` 與內建樣式）。

## 自訂轉換器

```python
from doc2html import Doc2Html, DocumentConverter, DocumentConverterResult

class MyConverter(DocumentConverter):
    priority = 10.0
    def accepts(self, file_stream, stream_info):
        return (stream_info.extension or "").lower() == ".myfmt"
    def convert(self, file_stream, stream_info):
        text = file_stream.read().decode("utf-8")
        return DocumentConverterResult(f"<p>{text}</p>", title="My Format")

engine = Doc2Html()
engine.register_converter(MyConverter())   # 同優先序時，後註冊者優先
```

## 開發

```bash
pip install -e '.[dev]'   # 安裝全部格式依賴 + pytest + ruff + reportlab
pytest                    # 跑測試（缺某格式套件時，相關測試自動 skip）
ruff check .              # lint
```

測試會在 `tmp_path` 動態產生各格式樣本（不依賴 repo 內的二進位檔），
涵蓋各轉換器輸出、分派優先序、兜底、缺依賴與錯誤訊息等情境。
CI 設定在 `.github/workflows/ci.yml`，於 Python 3.10–3.13 上跑 lint + test。

## 授權

MIT（見 [LICENSE](LICENSE)）
