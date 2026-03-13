# Research & Design Decisions — phase1-foundation

---
- **Feature**: `phase1-foundation`
- **Discovery Scope**: New Feature（`pipeline/` ディレクトリが未存在。完全に新規実装）
- **Key Findings**:
  - `pdf2image` は `poppler` のシステムインストールが前提。Windows では `poppler-windows` バイナリが必要
  - `StepResult` を dataclass で定義することで mypy strict との整合性が確保できる
  - Audiveris は 300dpi 未満では認識精度が著しく低下するため、解像度ゲートは入力段で必須

---

## Research Log

### pdf2image と poppler の依存関係

- **Context**: `pdf2image` が Python から PDF→PNG 変換に使う唯一の実用的ライブラリ
- **Sources Consulted**: pdf2image PyPI ページ、poppler-windows GitHub リリース
- **Findings**:
  - `pdf2image` は内部で `pdftoppm` (poppler ツール) を subprocess 経由で呼ぶ
  - Windows では `poppler` は自動インストールされず、バイナリ配布版を手動配置 or `conda install poppler` が必要
  - `convert_from_path(pdf_path, dpi=300)` で 300dpi PNG リストを返す
  - マルチページ PDF は各ページの `PIL.Image` リストとして返る → 個別に保存が必要
- **Implications**: `pyproject.toml` に `pdf2image` を追加済み。README に poppler インストール手順が必要。Unit テストでは PDF 変換をモック化して Java/poppler 不要にする

### OpenCV デスキュー実装方針

- **Context**: 傾き補正に Hough 変換を使う設計だが、楽譜画像への適用で注意点がある
- **Findings**:
  - 楽譜のスタッフライン（五線）は水平線の集合なので `HoughLinesP` で主要水平線を抽出し平均角度を計算する方法が有効
  - 回転は `cv2.getRotationMatrix2D` + `cv2.warpAffine` で実施
  - ±10度を超える傾きは意図的な縦書き楽譜の可能性があるため警告のみとし強制補正しない
- **Implications**: `Preprocessor` の `deskew()` は内部で `_detect_skew_angle()` と `_rotate_image()` に分離する

### StepResult の設計オプション比較

- **Context**: ドメイン間インターフェースをどのデータ型で表現するか
- **Alternatives**:
  1. TypedDict — 軽量だが mypy の型チェックが弱い
  2. dataclass — Python 3.7+ 標準、`__init__` 自動生成、mypy strict 対応
  3. Pydantic BaseModel — バリデーション豊富だが依存追加
- **Selected**: dataclass（標準ライブラリのみ、mypy strict 対応、シリアライズ要件なし）

---

## Architecture Pattern Evaluation

| オプション | 説明 | 強み | リスク |
|-----------|------|------|--------|
| モジュール直列パイプライン | 各ドメインが前のドメインの出力 Path を受け取り処理 | シンプル、テストしやすい | 並列化が難しい |
| ファイルパス疎結合（採用） | `StepResult.output_path` を経由して疎結合 | ドメイン間 import 不要、ステップキャッシュが自然に実装できる | オーバーヘッドは微小 |

---

## Design Decisions

### Decision: `pipeline/common.py` に StepResult と PipelineError を集約

- **Context**: 全ドメインで共通型が必要
- **Selected Approach**: `pipeline/common.py` 1ファイルに `StepResult` dataclass と `PipelineError` 基底クラスを定義
- **Rationale**: 依存方向を `common.py ← 各ドメイン` に統一することでドメイン間の循環 import を防ぐ
- **Trade-offs**: ファイルが増えるにつれて `common.py` が肥大化するリスクあり → Phase 2 以降で `pipeline/types.py` へ分割を検討

### Decision: キャッシュ設計は出力ディレクトリの存在チェックのみ（Phase 1 簡略版）

- **Context**: ステップキャッシュ必須の鉄則に従いながら Phase 1 の実装コストを抑える
- **Selected Approach**: 出力ファイルが既に存在する場合は再処理をスキップ。ソースファイルのハッシュ比較は Phase 2 以降
- **Trade-offs**: ソースファイルが変更されてもキャッシュが再利用される。開発中は `--no-cache` フラグで回避

---

## Risks & Mitigations

- **poppler 未インストール（Windows）** — `README.md` にインストール手順を記載。Unit テストでは `pdf2image` をモック化して依存回避
- **デスキュー過補正** — ±10度超は補正しない設計で緩和。unit テストで境界値テスト必須
- **mypy strict でのロールバック** — `dataclass` を使うことで型安全性を確保。`structlog` の型スタブは `types-*` パッケージで解決

---

## References

- [pdf2image PyPI](https://pypi.org/project/pdf2image/) — PDF変換実装
- [poppler-windows releases](https://github.com/oschwartz10612/poppler-windows/releases) — Windows バイナリ
- [OpenCV getRotationMatrix2D](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html) — 画像回転実装
- `docs/DESIGN.md § 2-1` — 前処理ステップ仕様
- `docs/phase1-foundation.md` — タスクリストと完了基準
