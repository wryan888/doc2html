# Changelog

本專案的所有重要變更都記錄於此。格式參考 [Keep a Changelog](https://keepachangelog.com/)，
版本遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

## [0.5.0] - 2026-06-06

### Added
- **公開 HTML 組裝 API**：新增 `doc2html.html` 模組，把原本內部的 `escape` /
  `tag` / `void_tag` / `paragraphs` / `table` / `image_data_uri` / `document`
  公開，供外部專案重用一致的跳脫與文件模板。
- `document()` 新增選用參數 `css`，可整組覆寫內建樣式（例如深色主題）；
  未傳入時行為與先前相同（向後相容）。

## [0.4.0] - 2026-06-06

### Added
- **掃描 PDF 的可插拔 OCR**：新增 `OcrBackend` 介面與內建 `GeminiOcr`
  （Google Gemini vision）。PDF 轉換器在某頁無文字層時，用 pypdfium2 把該頁
  rasterize 成 PNG，交給後端轉成 HTML。
- `Doc2Html(ocr=...)` 與 CLI `--ocr {none,gemini}` / `--ocr-model`。
- 新增 extras：`ocr`（pypdfium2 + pillow，rasterize，後端無關）、
  `ocr-gemini`（再加 google-genai）。

### Notes
- **預設不啟用、不外連**：未傳入 `ocr=` 時行為與先前相同（掃描檔僅提示需 OCR）。
- 啟用後文件頁面會送到雲端 API（隱私/成本請自行評估）；prompt 已明確要求
  忠實轉錄、禁止捏造，以降低幻覺風險。
- 後端可換：自訂類別實作 `image_to_html(png, *, lang)` 即可接 Tesseract / 其他
  vision LLM。

## [0.3.0] - 2026-06-06

### Added
- **DOCX 書籤**：`w:bookmarkStart` → `<a id="name">`，作為內部錨點跳轉目標。
  搭配 v0.2 的 `<a href="#anchor">`，Word 目錄/交叉參考的文件內導覽現在
  在輸出的 HTML 裡真正可用（自動略過 Word 插入的 `_GoBack`）。

### Notes
- 仍未支援：以 field code 產生的 TOC（`PAGEREF`/`HYPERLINK` 欄位）、
  表格儲存格內的書籤（儲存格目前以純文字輸出）。

## [0.2.1] - 2026-06-06

### Fixed
- `MissingDependencyException` docstring 仍寫 pdfminer，更正為 pdfplumber。
- PPTX 圖片擷取失敗時不再靜默吞錯，改為 `logger.debug`。

### Added（測試與文件）
- 補測試：DOCX 內部錨點超連結、`max_image_bytes` 閾值退化、PDF
  「標題→表格→內文」交錯順序、CLI 圖片旗標、pdfplumber 缺依賴。（35 → 41）
- README 說明 `register_converter()` 不會自動繼承圖片選項。
- 新增本 CHANGELOG。

## [0.2.0] - 2026-06-06

### Added
- **DOCX 超連結**：走訪段落 XML 處理 `w:hyperlink`，外部連結用 rels
  解析成 `<a href>`，內部錨點轉 `#anchor`。
- **DOCX / PPTX 圖片**：以 base64 data URI 內嵌成 `<img>`，可用
  `embed_images` / `max_image_bytes` 控制（超大或關閉則退化為文字佔位）。
- **PDF 表格抽取**：`find_tables()` 抽表格、過濾表格框內文字，再依垂直
  位置把段落/標題/表格交錯排序。
- CLI 新增 `--no-embed-images` / `--max-image-bytes`。
- 基底 `DocumentConverter` 新增 `embed_images` / `max_image_bytes` 共用選項。

### Changed
- **⚠ Breaking（僅影響 `pdf` extra 的依賴）**：PDF 轉換器由 `pdfminer.six`
  改為 `pdfplumber`（內含 pdfminer.six）。`pip install 'doc2html[pdf]'`
  現在安裝的是 pdfplumber；只用 pdfminer 的自訂整合需自行調整。

## [0.1.0] - 2026-06-06

### Added
- 初版：插件式轉換器架構（PDF / DOCX / XLSX / PPTX / HTML / CSV / JSON /
  純文字），CLI + Python API，輸出含完整文件模板的 HTML。
- 工程基礎：pytest 測試、ruff lint、GitHub Actions CI（Python 3.10–3.13）、
  sdist/wheel 打包、MIT 授權。

[0.4.0]: https://github.com/wryan888/doc2html/releases/tag/v0.4.0
[0.3.0]: https://github.com/wryan888/doc2html/releases/tag/v0.3.0
[0.2.1]: https://github.com/wryan888/doc2html/releases/tag/v0.2.1
[0.2.0]: https://github.com/wryan888/doc2html/releases/tag/v0.2.0
[0.1.0]: https://github.com/wryan888/doc2html/releases/tag/v0.1.0
