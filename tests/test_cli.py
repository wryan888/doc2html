"""CLI (__main__) 的 smoke test。"""

import io

from doc2html.__main__ import main


def test_cli_fragment(csv_file, capsys):
    rc = main([str(csv_file), "--fragment"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "<table>" in out
    assert "<!DOCTYPE html>" not in out  # 片段模式不含文件外殼


def test_cli_full_document(csv_file, capsys):
    rc = main([str(csv_file)])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("<!DOCTYPE html>")


def test_cli_output_file(csv_file, tmp_path):
    out_path = tmp_path / "out.html"
    rc = main([str(csv_file), "-o", str(out_path)])
    assert rc == 0
    assert out_path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_cli_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"a,b\n1,2")))
    rc = main(["--extension", ".csv", "--fragment"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "<th>a</th>" in out


def test_cli_error_returns_1(tmp_path, capsys):
    # 二進位、無副檔名 → 找不到轉換器 → 回傳 1
    bad = tmp_path / "blob"
    bad.write_bytes(b"\x00\x01\x02\xff")
    rc = main([str(bad)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "錯誤" in err
