"""doc2html 的命令列介面。

範例：
    doc2html report.pdf > report.html
    doc2html data.xlsx -o data.html
    cat notes.txt | doc2html --extension .txt
    doc2html page.html --fragment      # 只輸出 body 片段
"""

from __future__ import annotations

import argparse
import io
import sys

from . import __version__
from ._doc2html import Doc2Html
from ._exceptions import Doc2HtmlException
from ._stream_info import StreamInfo


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doc2html",
        description="把 PDF / Word / Excel / PowerPoint / HTML / CSV / "
        "JSON / 純文字 轉成 HTML。",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="輸入檔案路徑；省略則從 stdin 讀取。",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="輸出檔案路徑；省略則輸出到 stdout。",
    )
    parser.add_argument(
        "-e",
        "--extension",
        help="從 stdin 讀取時，指定副檔名提示（例如 .csv）。",
    )
    parser.add_argument(
        "--mime",
        help="手動指定 MIME type 提示。",
    )
    parser.add_argument(
        "--title",
        help="覆寫輸出 HTML 的 <title>。",
    )
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="只輸出 <main> 內的 HTML 片段，不含完整文件外殼。",
    )
    parser.add_argument(
        "--no-embed-images",
        action="store_false",
        dest="embed_images",
        help="不要把圖片內嵌為 base64，改輸出文字佔位（DOCX/PPTX）。",
    )
    parser.add_argument(
        "--max-image-bytes",
        type=int,
        default=2_000_000,
        help="單張圖片內嵌大小上限（位元組），超過則退化為佔位（預設 2000000）。",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"doc2html {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    engine = Doc2Html(
        embed_images=args.embed_images,
        max_image_bytes=args.max_image_bytes,
    )

    try:
        if args.input:
            result = engine.convert(
                args.input,
                stream_info=StreamInfo(
                    extension=args.extension, mimetype=args.mime
                ),
                title=args.title,
            )
        else:
            data = sys.stdin.buffer.read()
            result = engine.convert_stream(
                io.BytesIO(data),
                stream_info=StreamInfo(
                    extension=args.extension, mimetype=args.mime
                ),
                title=args.title,
            )
    except Doc2HtmlException as exc:
        print(f"doc2html: 錯誤：{exc}", file=sys.stderr)
        return 1

    output = result.body_html if args.fragment else result.html

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"已寫入 {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
