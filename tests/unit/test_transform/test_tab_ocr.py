"""tests for TAB OCR helper behavior."""

from __future__ import annotations

from pathlib import Path


def test_extract_tokens_returns_warning_when_tesseract_missing(monkeypatch, tmp_path: Path) -> None:
    from pipeline.transform.tab_ocr import TabOcrScanner

    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(
        TabOcrScanner,
        "_resolve_tesseract_path",
        staticmethod(lambda _path: None),
    )
    result = TabOcrScanner.extract_tokens(image_path)

    assert result.tokens == []
    assert result.warnings == ["TAB OCR skipped: tesseract executable not found"]


def test_resolve_tesseract_path_uses_default_windows_location(monkeypatch, tmp_path: Path) -> None:
    from pipeline.transform.tab_ocr import TabOcrScanner

    fake_install = tmp_path / "Tesseract-OCR" / "tesseract.exe"
    fake_install.parent.mkdir(parents=True)
    fake_install.write_text("", encoding="utf-8")

    monkeypatch.setattr("pipeline.transform.tab_ocr._DEFAULT_TESSERACT_LOCATIONS", (fake_install,))
    monkeypatch.setattr("pipeline.transform.tab_ocr.shutil.which", lambda _name: None)
    monkeypatch.delenv("TESSERACT_PATH", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    resolved = TabOcrScanner._resolve_tesseract_path(None)

    assert resolved == fake_install


def test_parse_tsv_tokens_assigns_staff_group_and_string() -> None:
    from pipeline.transform.tab_ocr import TabOcrScanner

    tsv_text = "\n".join(
        [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t100\t18\t10\t8\t92\t3",
            "5\t1\t1\t1\t1\t2\t140\t42\t10\t8\t88\t10",
            "5\t1\t1\t1\t1\t3\t180\t90\t10\t8\t12\t7",
        ]
    )

    tokens = TabOcrScanner._parse_tsv_tokens(
        tsv_text,
        [[20, 32, 44, 56, 68, 80]],
    )

    assert len(tokens) == 2
    assert tokens[0].staff_group == 0
    assert tokens[0].string == 6
    assert tokens[0].fret == 3
    assert tokens[1].string == 4
    assert tokens[1].fret == 10


def test_extract_tokens_uses_detected_staff_groups_and_tesseract_output(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from pipeline.transform.tab_ocr import TabOcrScanner, TabOcrToken

    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"fake")
    fake_tesseract = tmp_path / "tesseract.exe"
    fake_tesseract.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        TabOcrScanner,
        "_detect_tab_staff_groups",
        staticmethod(lambda _path: [[20, 32, 44, 56, 68, 80]]),
    )
    monkeypatch.setattr(
        TabOcrScanner,
        "_run_tesseract_tsv",
        staticmethod(
            lambda _image_path, _tesseract_path: "\n".join(
                [
                    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
                    "5\t1\t1\t1\t1\t1\t100\t18\t10\t8\t92\t3",
                ]
            )
        ),
    )
    monkeypatch.setattr(
        TabOcrScanner,
        "_scan_tokens_by_staff_rows",
        staticmethod(
            lambda _image_path, *, tesseract_path, staff_groups: [
                TabOcrToken(
                    staff_group=0,
                    string=4,
                    fret=10,
                    x=140,
                    y=42,
                    confidence=88.0,
                )
            ]
        ),
    )

    result = TabOcrScanner.extract_tokens(image_path, tesseract_path=fake_tesseract)

    assert result.warnings == []
    assert result.tesseract_path == fake_tesseract
    assert [(token.string, token.fret) for token in result.tokens] == [(6, 3), (4, 10)]
