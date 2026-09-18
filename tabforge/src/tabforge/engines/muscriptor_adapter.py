"""MuScriptor アダプタ（実装指示書 T1-4）。

⚠検証必須: `NoteStartEvent`/`NoteEndEvent` の実属性名・`index` による対応付け・
`instruments` の実測名は `scripts/probe_muscriptor.py` で確認するまで未確定。
ここでは 01_TabForge_詳細設計書.md §2.1 の記述に基づく想定 API で実装し、
`muscriptor` パッケージは呼び出し時にのみ import する（未インストールでも
`import tabforge.engines.muscriptor_adapter` 自体は失敗しない）。
"""
from __future__ import annotations

from pathlib import Path

from tabforge.ir.models import Note


class MuScriptorUnavailable(RuntimeError):
    """muscriptor がインストールされていない、またはライセンス未同意。"""


class MuScriptorEngine:
    def __init__(
        self,
        model: str = "medium",
        beam_size: int = 1,
        batch_size: int | None = None,
        device: str = "cuda",
    ) -> None:
        self.model_name = model
        self.beam_size = beam_size
        self.batch_size = batch_size
        self.device = device
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from muscriptor import TranscriptionModel
        except ImportError as exc:  # pragma: no cover - この環境では常に発生する
            raise MuScriptorUnavailable(
                "muscriptor がインストールされていません。"
                "`pip install -e '.[ml]'` に加え HuggingFace でのライセンス同意"
                "（CC BY-NC 4.0）が必要です。"
            ) from exc
        self._model = TranscriptionModel.load_model(self.model_name)
        return self._model

    def transcribe(self, audio: Path, instruments: list[str], run_id: str) -> list[Note]:
        """NoteStartEvent/NoteEndEvent を index で対応付けて Note に変換する。

        - instruments は呼び出し側で config/instruments.yaml の実測値に対して
          検証してから渡すこと。
        - velocity は存在しないので conf=1.0 固定（融合時に投票で上書きする）。
        - ProgressEvent は無視する（CLI 側で rich のプログレスバーに流す場合は
          ここでコールバックを追加する）。
        """
        model = self._load()
        kwargs: dict = {}
        if self.batch_size is not None:
            kwargs["batch_size"] = self.batch_size
        if self.beam_size and self.beam_size > 1:
            kwargs["beam_size"] = self.beam_size
            kwargs["use_sampling"] = False

        events = model.transcribe(str(audio), instruments=instruments, **kwargs)

        starts: dict[int, object] = {}
        notes: list[Note] = []
        counter = 0
        for event in events:
            cls_name = type(event).__name__
            if cls_name == "ProgressEvent":
                continue
            if cls_name == "NoteStartEvent":
                starts[event.index] = event
                continue
            if cls_name == "NoteEndEvent":
                start = event.start_event
                start_index = getattr(start, "index", None)
                starts.pop(start_index, None)
                counter += 1
                notes.append(
                    Note(
                        id=f"{run_id}_{counter:06d}",
                        onset=float(start.start_time),
                        offset=float(event.end_time),
                        pitch=int(start.pitch),
                        instrument=str(start.instrument),
                        conf=1.0,
                        votes=[run_id],
                        src_run=run_id,
                    )
                )
        return notes
