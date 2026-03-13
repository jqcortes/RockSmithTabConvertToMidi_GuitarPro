"""MusicXmlFinder ユニットテスト — Task 5: MusicXML 探索・検証"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from pipeline.omr.errors import OmrOutputError


def _write_valid_xml(path: Path) -> None:
    """well-formed な MusicXML を書き込むヘルパー"""
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<score-partwise><part-list/></score-partwise>",
        encoding="utf-8",
    )


def _write_invalid_xml(path: Path) -> None:
    """well-formed でない XML を書き込むヘルパー"""
    path.write_text("<unclosed-tag>broken xml", encoding="utf-8")


def _create_mxl(mxl_path: Path, inner_xml_name: str = "score.xml") -> None:
    """.mxl（ZIP 内 XML）を作成するヘルパー"""
    valid_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<score-partwise><part-list/></score-partwise>"
    )
    with zipfile.ZipFile(mxl_path, "w") as zf:
        zf.writestr(inner_xml_name, valid_xml)


def _create_invalid_mxl(mxl_path: Path) -> None:
    """well-formed でない XML を含む .mxl を作成するヘルパー"""
    with zipfile.ZipFile(mxl_path, "w") as zf:
        zf.writestr("score.xml", "<broken>unclosed")


class TestMusicXmlFinderMxlPriority:
    """.mxl が優先して探索されること"""

    def test_finds_mxl_when_present(self, tmp_path: Path) -> None:
        """.mxl ファイルが存在する場合に返されること"""
        from pipeline.omr.finder import MusicXmlFinder

        _create_mxl(tmp_path / "score.mxl")
        result = MusicXmlFinder.find(tmp_path, "score")
        assert result == tmp_path / "score.mxl"

    def test_mxl_preferred_over_xml(self, tmp_path: Path) -> None:
        """.mxl と .xml が両方ある場合 .mxl が優先されること"""
        from pipeline.omr.finder import MusicXmlFinder

        _create_mxl(tmp_path / "score.mxl")
        xml_path = tmp_path / "score.xml"
        _write_valid_xml(xml_path)

        result = MusicXmlFinder.find(tmp_path, "score")
        assert result.suffix == ".mxl"

    def test_returns_path_object(self, tmp_path: Path) -> None:
        """戻り値が Path オブジェクトであること"""
        from pipeline.omr.finder import MusicXmlFinder

        _create_mxl(tmp_path / "score.mxl")
        result = MusicXmlFinder.find(tmp_path, "score")
        assert isinstance(result, Path)


class TestMusicXmlFinderXmlFallback:
    """.mxl が存在しない場合 .xml にフォールバックすること"""

    def test_finds_xml_when_no_mxl(self, tmp_path: Path) -> None:
        """.xml が存在する場合に返されること"""
        from pipeline.omr.finder import MusicXmlFinder

        xml_path = tmp_path / "score.xml"
        _write_valid_xml(xml_path)

        result = MusicXmlFinder.find(tmp_path, "score")
        assert result == xml_path

    def test_xml_fallback_returns_path(self, tmp_path: Path) -> None:
        """.xml フォールバック時の戻り値が Path であること"""
        from pipeline.omr.finder import MusicXmlFinder

        xml_path = tmp_path / "myscore.xml"
        _write_valid_xml(xml_path)

        result = MusicXmlFinder.find(tmp_path, "myscore")
        assert isinstance(result, Path)
        assert result.suffix == ".xml"


class TestMusicXmlFinderNotFound:
    """MusicXML が見つからない場合は OmrOutputError"""

    def test_empty_dir_raises(self, tmp_path: Path) -> None:
        """出力ディレクトリが空の場合 OmrOutputError を raise すること"""
        from pipeline.omr.finder import MusicXmlFinder

        with pytest.raises(OmrOutputError):
            MusicXmlFinder.find(tmp_path, "score")

    def test_no_mxl_or_xml_raises(self, tmp_path: Path) -> None:
        """.mxl も .xml も存在しない場合 OmrOutputError を raise すること"""
        from pipeline.omr.finder import MusicXmlFinder

        (tmp_path / "score.omr").write_text("omr data")
        (tmp_path / "score.png").write_text("png data")

        with pytest.raises(OmrOutputError):
            MusicXmlFinder.find(tmp_path, "score")

    def test_error_message_contains_output_dir(self, tmp_path: Path) -> None:
        """OmrOutputError のメッセージに出力ディレクトリが含まれること"""
        from pipeline.omr.finder import MusicXmlFinder

        with pytest.raises(OmrOutputError) as exc_info:
            MusicXmlFinder.find(tmp_path, "score")

        assert str(tmp_path) in str(exc_info.value)


class TestMusicXmlFinderMxlValidation:
    """.mxl が well-formed であることを検証すること"""

    def test_valid_mxl_does_not_raise(self, tmp_path: Path) -> None:
        """well-formed な .mxl は例外なし"""
        from pipeline.omr.finder import MusicXmlFinder

        _create_mxl(tmp_path / "score.mxl")
        result = MusicXmlFinder.find(tmp_path, "score")
        assert result.exists()

    def test_invalid_mxl_raises_omr_output_error(self, tmp_path: Path) -> None:
        """well-formed でない .mxl は OmrOutputError を raise すること"""
        from pipeline.omr.finder import MusicXmlFinder

        _create_invalid_mxl(tmp_path / "score.mxl")
        with pytest.raises(OmrOutputError):
            MusicXmlFinder.find(tmp_path, "score")

    def test_invalid_mxl_error_contains_path(self, tmp_path: Path) -> None:
        """エラーメッセージに .mxl ファイルパスが含まれること"""
        from pipeline.omr.finder import MusicXmlFinder

        mxl_path = tmp_path / "score.mxl"
        _create_invalid_mxl(mxl_path)
        with pytest.raises(OmrOutputError) as exc_info:
            MusicXmlFinder.find(tmp_path, "score")

        assert "score.mxl" in str(exc_info.value)

    def test_not_a_zip_mxl_raises(self, tmp_path: Path) -> None:
        """ZIP でない .mxl ファイルは OmrOutputError を raise すること"""
        from pipeline.omr.finder import MusicXmlFinder

        mxl_path = tmp_path / "score.mxl"
        mxl_path.write_text("this is not a zip file", encoding="utf-8")
        with pytest.raises(OmrOutputError):
            MusicXmlFinder.find(tmp_path, "score")


class TestMusicXmlFinderXmlValidation:
    """.xml が well-formed であることを検証すること"""

    def test_valid_xml_does_not_raise(self, tmp_path: Path) -> None:
        """well-formed な .xml は例外なし"""
        from pipeline.omr.finder import MusicXmlFinder

        xml_path = tmp_path / "score.xml"
        _write_valid_xml(xml_path)
        result = MusicXmlFinder.find(tmp_path, "score")
        assert result == xml_path

    def test_invalid_xml_raises_omr_output_error(self, tmp_path: Path) -> None:
        """well-formed でない .xml は OmrOutputError を raise すること"""
        from pipeline.omr.finder import MusicXmlFinder

        xml_path = tmp_path / "score.xml"
        _write_invalid_xml(xml_path)
        with pytest.raises(OmrOutputError):
            MusicXmlFinder.find(tmp_path, "score")

    def test_invalid_xml_error_contains_path(self, tmp_path: Path) -> None:
        """エラーメッセージに .xml ファイルパスが含まれること"""
        from pipeline.omr.finder import MusicXmlFinder

        xml_path = tmp_path / "score.xml"
        _write_invalid_xml(xml_path)
        with pytest.raises(OmrOutputError) as exc_info:
            MusicXmlFinder.find(tmp_path, "score")

        assert "score.xml" in str(exc_info.value)
