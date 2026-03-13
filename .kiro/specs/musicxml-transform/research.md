# Research & Design Decisions — musicxml-transform

---
**Purpose**: 設計フェーズで調査した内容・アーキテクチャ上のトレードオフ・根拠をまとめる。

---

## Summary

- **Feature**: `musicxml-transform`
- **Discovery Scope**: New Feature（`pipeline/transform/` ディレクトリは未実装。グリーンフィールド）
- **Key Findings**:
  - `pipeline/omr/` の 7 ファイルパターンをそのまま踏襲できる（errors / validator / fixer / identifier / filter / _transform / __init__）
  - MusicXML 操作には **lxml 直接操作** が最適（music21 はオーバーキル、同プロジェクトで実績あり）
  - Audiveris は標準 MusicXML にノート単位の信頼度スコアを出力しない。`confidence_filter.py` はインフラのみ実装し、今は「属性なし → 信頼度 1.0」としてパスする設計とする

---

## Research Log

### Topic 1: Audiveris の信頼度スコアが MusicXML に含まれるか

- **Context**: 要件 4 では `quality_score < 0.5` のノートを除外する必要があるが、Audiveris が個々のノートに対する信頼度を MusicXML に埋め込むかどうか不明だった（R-1）
- **Sources Consulted**:
  - `docs/audiveris-cli-reference.md`（ローカル）
  - Audiveris 5.x の MusicXML 出力仕様（`-export` フラグ）
  - `pipeline/omr/runner.py` の `DEFAULT_OPTIONS`（`minGrade=0.35`）
- **Findings**:
  - Audiveris の `-export` は MXL 標準 (W3C MusicXML 4.0) に準拠した XML を生成する
  - 標準 MusicXML にはノート単位の OMR 信頼度フィールドが存在しない
  - `minGrade=0.35` は **Audiveris 内部の SIG (Symbol Interpretation Graph) フィルタ**であり、グレードが低いノートはそもそも MusicXML に出力されない（出力済みノートはすべてグレード ≥ 0.35 を満たす）
  - Audiveris は `.omr` ブックファイル（独自バイナリ形式）に各シンボルのグレードを保存するが、これは CLI `-export` では MusicXML に伝播しない
- **Implications**:
  - 現フェーズでは `confidence_filter.py` は「信頼度属性が存在する場合のみフィルタを適用し、なければ 1.0 とみなしてスキップ」する実装とする
  - 将来的に品質 (Quality) ドメインが独自スコアを MusicXML に付与するカスタム属性を定義した際に、同フィルタが機能するよう拡張ポイントを設ける

---

### Topic 2: music21 vs lxml — MusicXML 変換ライブラリ選定

- **Context**: TAB フレット情報の読み取りとピッチ上書きに使うライブラリを選定する必要があった
- **Sources Consulted**:
  - `pyproject.toml`（`music21>=9.0`、`lxml>=4.0` 両方インストール済み）
  - `pipeline/omr/finder.py`（lxml で `.mxl`/`.xml` の well-formed 検証実績あり）
  - music21 9.9.1 ドキュメント（`note.Note`, `stream.Part`, `notations` API）
- **Findings**:
  - **music21**: `converter.parse()` が MusicXML を完全なオブジェクトモデルに変換する。TAB フレットは `note.articulations` / `note.notations` 経由でアクセス可能だが、TAB clef 識別は `staff.clef` → `TabClef` インスタンス確認が必要。変換後の serialize には `stream.write('musicxml')` を使い、内部フォーマットからの再 serialization でノート属性が変化するリスクあり
  - **lxml**: XML ツリーを直接操作する。`<technical><fret>` `<technical><string>` `<clef sign="TAB">` は XPath で確実に取得可能。serialization は `etree.tostring()` で入力 XML を最小限変更するだけ。`pipeline/omr/finder.py` で既に well-formed 検証に使用済み（チームの習熟度あり）
- **Implications**:
  - **lxml を採用**: 外科的な XML パッチに特化しており、music21 オブジェクトモデルへの依存を回避できる。serialize 安全性が高い。OMR ドメインとのコンシステンシーも確保される
  - music21 は将来 Render ドメイン（MIDI 生成）で `stream.write('midi')` に使用する際に本領発揮させる

---

### Topic 3: XML 変換パイプラインの内部データフロー設計

- **Context**: バリデーション → ギター補正 → パート識別 → 信頼度フィルタの順で変換が必要。各ステップ間のデータ受け渡し方式を決定する必要があった
- **Findings**:
  - `etree._ElementTree` を内部通貨として各変換器が受け取り・返す **Transformer Chain** パターンが最もシンプル
  - 中間ファイルを書くと I/O コストが増加しキャッシュ判定が複雑になる
  - ファイル I/O は最初（バリデーション時の読み込み）と最後（補正済み XML の書き出し）のみ
- **Implications**:
  - `MusicXmlValidator.validate() → etree._ElementTree` を起点に、各コンポーネントが `etree._ElementTree` を受け取り返す設計とする

---

## Architecture Pattern Evaluation

| Option | 説明 | 強み | リスク/制限 | 評価 |
|--------|------|------|------------|------|
| OMR パターン踏襲（lxml + 個別モジュール） | `pipeline/omr/` と同構成で `transform/` を新規作成 | チームの習熟度あり・設計一貫性・テスト独立性 | なし（グリーンフィールドのため互換性問題なし） | **採用** |
| music21 オブジェクトモデル全面採用 | `converter.parse()` → music21 操作 → `stream.write()` | Python API が高水準で読みやすい | serialize 安全性リスク・依存重量化・Render 段階での二重変換 | 不採用 |
| 単一モジュール実装 | `transform.py` 1 ファイルにすべてまとめる | ファイル数が少ない | 責務混在・テスト分離困難・OMR パターンとの不整合 | 不採用 |

---

## Design Decisions

### Decision: lxml を Transform ドメインの XML 操作ライブラリとして採用する

- **Context**: `guitar_fixer.py` での TAB フレット→pitch 上書きおよびネームスペース対応 MusicXML の serialization
- **Alternatives Considered**:
  1. music21 — 高水準 API だが serialize 安全性に懸念、Render と Transform で同じライブラリを使うと責務が不明確になる
  2. lxml — 低水準 XML 直接操作、OMR で実績あり
- **Selected Approach**: lxml で `etree._ElementTree` を内部通貨として使い、XPath で `<technical><fret>` / `<technical><string>` を取得してピッチ計算・書き換えを行う
- **Rationale**: serialization の副作用ゼロ・既存コードとの整合性・TAB 要素へのアクセスが確実
- **Trade-offs**: XPath 記述が verbose になるが、これは型安全な wrapper メソッドで吸収する
- **Follow-up**: MusicXML ネームスペース（`xmlns:...`）の有無を実際の Audiveris 出力で確認すること

---

### Decision: `confidence_filter.py` は現フェーズ「インフラのみ実装」とする

- **Context**: Audiveris は標準 MusicXML にノート単位の信頼度を出力しない（Topic 1 参照）
- **Selected Approach**: `ConfidenceFilter.filter()` は `confidence` 属性がないノートを信頼度 1.0 としてパスする。属性がある場合のみ閾値 (0.5) と比較して除外する
- **Rationale**: 要件 4 を実装しつつ、現実の Audiveris 出力に対してはノートを消さない安全な挙動を保証する
- **Follow-up**: Quality ドメインの実装時に `<note confidence="0.3">` 相当のカスタム属性定義を確立し、その後このフィルタを有効化する

---

### Decision: `config/instrument_map.yaml` を `pipeline/transform/` 実装と同時に新規作成する

- **Context**: TAB チューニング（standard/drop_d/half_step_down 等）を外部 YAML で管理する（要件 2.3）
- **Selected Approach**: `GuitarFixer` は `config/instrument_map.yaml` の `tunings:` セクションを `PyYAML`（stdlib の `json` / `tomllib` の代替、または `pyyaml`）で読み込む。ファイルが存在しない場合は `STANDARD_TUNING = [40, 45, 50, 55, 59, 64]` をデフォルトとして使用する
- **Trade-offs**: `pyaml` 依存追加が必要だが、`pyproject.toml` には未記載のため追加が必要

---

## Risks & Mitigations

- **R-1: Audiveris MusicXML ネームスペース変動** — `etree` XPath が `ns0:` プレフィックス付きになる可能性。`clark notation` または XPath `local-name()` で対処する
- **R-2: TAB スタッフの `<fret>` / `<string>` が空またはテキストが数値以外** — `guitar_fixer.py` でバリデーション + `TransformGuitarFixerError` で安全に失敗させる
- **R-3: `config/instrument_map.yaml` の不在** — `GuitarFixer` は `FileNotFoundError` を握りつぶさず、デフォルトチューニングで続行するように設計する
- **R-4: .mxl（ZIP）入力の serialize 後サイズ** — lxml で読み込み後、出力は圧縮なしの `.xml` に統一する（ファイルサイズは増加するが透明性向上）

## References

- [MusicXML 4.0 Technical Notes](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/technical/) — `<fret>`, `<string>`, `<bend>` 要素定義
- `pipeline/omr/finder.py` — lxml による MusicXML well-formed 検証の参照実装
- `docs/guitar-specific.md` — TAB 解析設計書・チューニング定義
- `docs/QUALITY_SCORE.md` — 品質スコア定義・0.5 閾値の根拠
- [Audiveris GitHub](https://github.com/Audiveris/audiveris) — MusicXML エクスポート実装（信頼度属性調査用）
