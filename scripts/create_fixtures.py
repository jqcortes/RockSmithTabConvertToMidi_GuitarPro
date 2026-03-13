"""テスト用フィクスチャを生成するスクリプト。"""
from pathlib import Path

from PIL import Image, ImageDraw

fixtures_dir = Path("tests/fixtures")
fixtures_dir.mkdir(parents=True, exist_ok=True)

# A4 at 300dpi
WIDTH, HEIGHT = 2480, 3508

# ---- 300dpi サンプル PNG（ギタースコア風: 五線譜+TAB譜線） ----
img = Image.new("L", (WIDTH, HEIGHT), color=255)
draw = ImageDraw.Draw(img)

for staff in range(2):
    y_base = 400 + staff * 600
    # 五線譜（5本線）
    for i in range(5):
        y = y_base + i * 30
        draw.line([(100, y), (WIDTH - 100, y)], fill=0, width=3)
    # TAB譜（6弦）
    y_tab_base = y_base + 200
    for i in range(6):
        y = y_tab_base + i * 25
        draw.line([(100, y), (WIDTH - 100, y)], fill=0, width=2)
    # フレット番号風の黒丸
    for x_pos in range(250, WIDTH - 200, 200):
        draw.ellipse([x_pos, y_tab_base + 10, x_pos + 20, y_tab_base + 30], fill=0)

img.save(str(fixtures_dir / "sample_score.png"), dpi=(300, 300))
size_kb = (fixtures_dir / "sample_score.png").stat().st_size / 1024
print(f"sample_score.png 保存完了: {size_kb:.1f} KB")

# ---- サンプル PDF（単一ページ、同内容） ----
img_rgb = Image.new("RGB", (WIDTH, HEIGHT), color=255)
draw_rgb = ImageDraw.Draw(img_rgb)

for staff in range(2):
    y_base = 400 + staff * 600
    for i in range(5):
        y = y_base + i * 30
        draw_rgb.line([(100, y), (WIDTH - 100, y)], fill=0, width=3)
    y_tab_base = y_base + 200
    for i in range(6):
        y = y_tab_base + i * 25
        draw_rgb.line([(100, y), (WIDTH - 100, y)], fill=0, width=2)
    for x_pos in range(250, WIDTH - 200, 200):
        draw_rgb.ellipse([x_pos, y_tab_base + 10, x_pos + 20, y_tab_base + 30], fill=0)

img_rgb.save(str(fixtures_dir / "sample_score.pdf"), resolution=300)
size_kb = (fixtures_dir / "sample_score.pdf").stat().st_size / 1024
print(f"sample_score.pdf 保存完了: {size_kb:.1f} KB")

print("tests/fixtures/ 作成完了")
