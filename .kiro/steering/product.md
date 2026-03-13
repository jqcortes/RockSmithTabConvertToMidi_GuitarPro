# Product Overview

バンドスコア（ギター楽譜、スキャン PDF/PNG）を MIDI ファイルに自動変換するローカル CLI パイプライン。
ギタリスト・DTM 制作者が手作業ゼロで楽譜を DAW 取り込み可能な形式に変換できることを目指す。

## Core Capabilities

1. **スキャン楽譜の自動認識**: PDF/PNG のバンドスコアを Audiveris OMR で MusicXML に変換
2. **タブ譜優先変換**: ギター TAB 記号のフレット情報を pitch の正解として採用し精度を向上
3. **MIDI Type 1 出力**: パート・テンポ・GM 楽器情報付きの MIDI を生成
4. **信頼度ベース品質保証**: 閾値未満のノートは除外し、quality_report.json で可視化
5. **ステップキャッシュ**: 各処理ステップを個別に再実行可能なキャッシュ設計

## Target Use Cases

- ギタータブ譜・バンドスコアを DAW (Logic Pro, Cubase 等) に取り込みたい
- 既存楽曲の耳コピ補助として OMR 変換結果を利用したい
- 大量の楽譜スキャンをバッチ処理で一括 MIDI 変換したい
- RockSmith 2014 の楽曲データを練習素材用 MIDI に変換したい

## Value Proposition

- **無補正体験**: 信頼度の低い結果を明示的に除外することで「修正不要」に近い体験を実現
- **ローカル処理**: クラウド不要・プライバシー安全・外部 API 課金なし
- **ギター特化**: 汎用 OMR ツールとは異なり、タブ譜・チョーキング等のギター特有記法を処理対象とする
- **透明なパイプライン**: 各ステップのスコアをログに記録し、精度劣化ポイントを即時診断可能

---
_Focus on patterns and purpose, not exhaustive feature lists_
