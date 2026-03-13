"""
pipeline/omr/errors.py — OMR ドメイン固有の例外階層

OmrError を PipelineError のサブクラスとして定義し、
OMR 処理の各失敗モード（環境・タイムアウト・実行・出力）を
型安全に表現する。

Exports:
    OmrError           — OMR ドメイン例外の基底クラス
    OmrEnvironmentError — Java/JAR 実行環境の問題
    OmrTimeoutError    — Audiveris CLI のタイムアウト
    OmrExecutionError  — Audiveris CLI の非0終了コード
    OmrOutputError     — MusicXML 出力の不在・破損
"""

from __future__ import annotations

from pipeline.common import PipelineError


class OmrError(PipelineError):
    """OMR ドメイン全般のエラー基底クラス。

    呼び出し元は `except OmrError` で一括 catch するか、
    サブクラスで個別 catch できる。
    """


class OmrEnvironmentError(OmrError):
    """Java 17+ が未インストール、または Audiveris JAR が見つからない場合。

    例: Java が PATH に存在しない、バージョンが 17 未満、
    設定された JAR ファイルが存在しない。
    """


class OmrTimeoutError(OmrError):
    """Audiveris CLI が設定されたタイムアウト秒数内に終了しなかった場合。

    プロセスは強制終了（kill）される。
    """


class OmrExecutionError(OmrError):
    """Audiveris CLI が 0 以外の終了コードで終了した場合。

    stderr の内容がメッセージに含まれる。
    """


class OmrOutputError(OmrError):
    """Audiveris CLI 実行後に期待される MusicXML が見つからない、
    または well-formed でない場合。
    """
