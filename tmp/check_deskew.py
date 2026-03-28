import cv2, math, numpy as np

img_raw = cv2.imread("tmp/crash_cache/ingest/CRASH_COMPLEXION_p003.png", cv2.IMREAD_GRAYSCALE)
gray = cv2.GaussianBlur(img_raw, (3, 3), 0)

# 現行方式: グレースケール直接
lines = cv2.HoughLinesP(gray, rho=1, theta=math.pi/180, threshold=100,
    minLineLength=gray.shape[1]//4, maxLineGap=20)
angles = [math.degrees(math.atan2(float(l[0][3]-l[0][1]), float(l[0][2]-l[0][0]))) for l in (lines if lines is not None else [])]
near10 = [a for a in angles if abs(a) <= 10.0]
print(f"[現行方式] lines={len(lines) if lines is not None else 0}  near<=10deg={len(near10)}  median={round(float(np.median(near10)),3) if near10 else 'N/A'}")

# 改善案: Canny + ±3° フィルタ + 幅1/3以上
edges = cv2.Canny(gray, 50, 150, apertureSize=3)
lines2 = cv2.HoughLinesP(edges, rho=1, theta=math.pi/180, threshold=100,
    minLineLength=gray.shape[1]//3, maxLineGap=10)
angles2 = [math.degrees(math.atan2(float(l[0][3]-l[0][1]), float(l[0][2]-l[0][0]))) for l in (lines2 if lines2 is not None else [])]
near3 = [a for a in angles2 if abs(a) <= 3.0]
print(f"[Canny+1/3] lines={len(lines2) if lines2 is not None else 0}  near<=3deg={len(near3)}  median={round(float(np.median(near3)),3) if near3 else 'N/A'}")

# ページ003, 004 の比較用に複数ページ確認
for page in ["p001","p002","p003","p004","p005"]:
    path = f"tmp/crash_cache/ingest/CRASH_COMPLEXION_{page}.png"
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    g = cv2.GaussianBlur(img, (3,3), 0)
    e = cv2.Canny(g, 50, 150, apertureSize=3)
    ls = cv2.HoughLinesP(e, rho=1, theta=math.pi/180, threshold=100,
        minLineLength=g.shape[1]//3, maxLineGap=10)
    a3 = [math.degrees(math.atan2(float(l[0][3]-l[0][1]), float(l[0][2]-l[0][0]))) for l in (ls if ls is not None else [])]
    n3 = [a for a in a3 if abs(a) <= 3.0]
    med = round(float(np.median(n3)),3) if n3 else "N/A"
    # 現行も確認
    ls0 = cv2.HoughLinesP(g, rho=1, theta=math.pi/180, threshold=100,
        minLineLength=g.shape[1]//4, maxLineGap=20)
    a0 = [math.degrees(math.atan2(float(l[0][3]-l[0][1]), float(l[0][2]-l[0][0]))) for l in (ls0 if ls0 is not None else [])]
    n0 = [a for a in a0 if abs(a) <= 10.0]
    med0 = round(float(np.median(n0)),3) if n0 else "N/A"
    print(f"  {page}: 現行={med0}°  Canny改善={med}°")
