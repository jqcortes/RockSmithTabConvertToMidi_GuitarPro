"""★S7 の定量評価（設計書 §12.2、実装指示書 T2-5）。

GuitarSet の弦・フレット正解ノートをそのまま `arrange.fretting.assign_frets`
に入力し、出力された (string, fret) を正解と比較して string/fret accuracy
を算出する。**正解ノート（ピッチ）を入力条件とする**ことで、採譜誤差と
フレット割当アルゴリズム自体の誤差を分離して評価できる（GuitarSet がこの
プロジェクトの要石とされる理由）。

⚠検証必須: 実際の GuitarSet JAMS アノテーション（弦別 note_midi 名前空間）の
パースは `jams` ライブラリの実データでの検証が必要。この実行環境にはデータ
セットが無いため、`load_guitarset_jams` は骨組みのみ実装している。
`evaluate_fretting` （本体の評価ロジック）はデータ形式に依存しないため
テスト済み。

使い方（データセットがある環境で）:
    uv run python eval/guitarset_fretting.py --data <guitarset_dir> --out eval/out/fretting.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tabforge.arrange.fretting import FretConfig, OnsetGroup, assign_frets


@dataclass(frozen=True)
class GroundTruthNote:
    onset: float
    offset: float
    pitch: int
    string: int  # GuitarSet 規則: 0 = 6弦(低音E) ... 5 = 1弦(高音e)
    fret: int


def _our_index_to_guitarset_string(index: int, n_strings: int) -> int:
    """本プロジェクトの index（0=最高音弦）→ GuitarSet の string（0=最低音弦）。"""
    return (n_strings - 1) - index


def load_guitarset_jams(path: Path) -> list[GroundTruthNote]:
    """GuitarSet の .jams アノテーションを読み込む（⚠検証必須、骨組みのみ）。

    実データでの検証ができていないため、呼び出すと明示的に未検証である旨の
    エラーを送出する。実データで確認でき次第、本関数を完成させること。
    """
    try:
        import jams  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "jams がインストールされていません。`pip install jams` してください。"
        ) from exc
    raise NotImplementedError(
        "GuitarSet JAMS パーサは実データでの検証待ち（この実行環境にはデータセットが無い）。"
        " string 別 note_midi アノテーションから GroundTruthNote へのマッピングを実装すること。"
    )


def _group_by_onset(notes: list[GroundTruthNote]) -> list[list[GroundTruthNote]]:
    """同一オンセット（和音）をまとめる。notes は onset 昇順を仮定する。"""
    groups: list[list[GroundTruthNote]] = []
    for note in notes:
        if groups and abs(note.onset - groups[-1][0].onset) < 1e-6:
            groups[-1].append(note)
        else:
            groups.append([note])
    return groups


def evaluate_fretting(
    ground_truth: list[GroundTruthNote], cfg: FretConfig
) -> dict[str, float]:
    """正解ノートの pitch のみを入力し、フレット割当単体の精度を測る。"""
    if not ground_truth:
        return {"string_accuracy": 0.0, "fret_accuracy": 0.0, "n_notes": 0, "n_in_range": 0}

    sorted_gt = sorted(ground_truth, key=lambda n: n.onset)
    gt_groups = _group_by_onset(sorted_gt)
    onset_groups = [OnsetGroup(pitches=[n.pitch for n in g]) for g in gt_groups]
    assignments = assign_frets(onset_groups, cfg)

    in_range_groups = [g for g, og in zip(gt_groups, onset_groups, strict=True) if og.warning is None]

    n_strings = len(cfg.tuning)
    string_correct = 0
    fret_correct = 0
    n_in_range = 0
    for gt_group, assign in zip(in_range_groups, assignments, strict=True):
        for gt, predicted in zip(gt_group, assign, strict=True):
            predicted_index, predicted_fret = predicted
            predicted_string = _our_index_to_guitarset_string(predicted_index, n_strings)
            n_in_range += 1
            if predicted_string == gt.string:
                string_correct += 1
            if predicted_fret == gt.fret:
                fret_correct += 1

    return {
        "string_accuracy": string_correct / n_in_range if n_in_range else 0.0,
        "fret_accuracy": fret_correct / n_in_range if n_in_range else 0.0,
        "n_notes": len(ground_truth),
        "n_in_range": n_in_range,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="GuitarSet データセットのディレクトリ")
    parser.add_argument("--out", type=Path, required=True, help="結果 JSON の出力先")
    parser.add_argument("--tuning", type=str, default="64,59,55,50,45,40",
                         help="カンマ区切り MIDI ノート番号 (index0=最高音弦)")
    args = parser.parse_args()

    tuning = tuple(int(x) for x in args.tuning.split(","))
    cfg = FretConfig(tuning=tuning)

    jams_files = sorted(args.data.rglob("*.jams"))
    if not jams_files:
        print(f"'{args.data}' に .jams ファイルが見つからない", file=sys.stderr)
        sys.exit(1)

    all_results = []
    for jams_path in jams_files:
        try:
            ground_truth = load_guitarset_jams(jams_path)
        except NotImplementedError as exc:
            print(f"skip {jams_path}: {exc}", file=sys.stderr)
            continue
        result = evaluate_fretting(ground_truth, cfg)
        result["file"] = str(jams_path)
        all_results.append(result)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out} ({len(all_results)} files evaluated)")


if __name__ == "__main__":
    main()
