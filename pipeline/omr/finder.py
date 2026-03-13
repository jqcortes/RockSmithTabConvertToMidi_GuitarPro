"""MusicXmlFinder — 出力 MusicXML の探索と well-formed 検証"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from lxml import etree

from pipeline.common import get_logger
from pipeline.omr.errors import OmrOutputError


class MusicXmlFinder:
    """出力ディレクトリから MusicXML ファイルを探索し検証するクラス。

    探索優先順: `*.mxl`（ZIP 圧縮）→ `*.xml`（非圧縮）
    どちらも見つからない、または well-formed でない場合は `OmrOutputError` を raise する。
    """

    @staticmethod
    def find(output_dir: Path, stem: str) -> Path:
        """output_dir 内の MusicXML ファイルを探索して検証済みパスを返す。

        Args:
            output_dir: Audiveris が MusicXML を書き込んだディレクトリ。
            stem: 入力画像のステム名（拡張子なし）。

        Returns:
            検証済みの MusicXML ファイルパス（.mxl または .xml）。

        Raises:
            OmrOutputError: ファイルが見つからない、または well-formed でない場合。
        """
        logger = get_logger(__name__)

        # .mxl 優先探索
        mxl_files = list(output_dir.glob("*.mxl"))
        if mxl_files:
            mxl_path = mxl_files[0]
            MusicXmlFinder._validate_mxl(mxl_path)
            logger.info("musicxml_found", path=str(mxl_path), format="mxl")
            return mxl_path

        # .xml フォールバック探索
        xml_files = list(output_dir.glob("*.xml"))
        if xml_files:
            xml_path = xml_files[0]
            MusicXmlFinder._validate_xml(xml_path)
            logger.info("musicxml_found", path=str(xml_path), format="xml")
            return xml_path

        raise OmrOutputError(
            f"MusicXML ファイルが出力ディレクトリに見つかりませんでした: {output_dir}"
        )

    @staticmethod
    def _validate_mxl(mxl_path: Path) -> None:
        """.mxl（ZIP 形式）を検証する。

        Raises:
            OmrOutputError: ZIP でない、または内部 XML が well-formed でない場合。
        """
        try:
            with zipfile.ZipFile(mxl_path, "r") as zf:
                xml_names = [
                    name for name in zf.namelist() if name.endswith(".xml")
                ]
                if not xml_names:
                    raise OmrOutputError(
                        f".mxl 内に XML ファイルが見つかりませんでした: {mxl_path}"
                    )
                xml_content = zf.read(xml_names[0])
        except zipfile.BadZipFile as exc:
            raise OmrOutputError(
                f".mxl ファイルが ZIP 形式ではありません: {mxl_path}"
            ) from exc

        try:
            etree.fromstring(xml_content)
        except etree.XMLSyntaxError as exc:
            raise OmrOutputError(
                f"MusicXML が well-formed ではありません: {mxl_path}"
            ) from exc

    @staticmethod
    def _validate_xml(xml_path: Path) -> None:
        """.xml ファイルを lxml で well-formed 検証する。

        Raises:
            OmrOutputError: well-formed でない場合。
        """
        try:
            etree.parse(str(xml_path))  # noqa: S320  # ローカルファイルのみ
        except etree.XMLSyntaxError as exc:
            raise OmrOutputError(
                f"MusicXML が well-formed ではありません: {xml_path}"
            ) from exc
