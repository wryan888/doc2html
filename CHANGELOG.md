# Changelog

本專案的所有重要變更都記錄於此。格式參考 [Keep a Changelog](https://keepachangelog.com/)，
版本遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

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

[0.2.1]: https://github.com/wryan888/doc2html/releases/tag/v0.2.1
[0.2.0]: https://github.com/wryan888/doc2html/releases/tag/v0.2.0
[0.1.0]: https://github.com/wryan888/doc2html/releases/tag/v0.1.0
