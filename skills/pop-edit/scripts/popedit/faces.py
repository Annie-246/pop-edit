"""Nhận diện mặt (YuNet của OpenCV) + nhận diện đường chia đôi của bố cục split. Dùng để đặt caption không che mặt."""
import json
import os

import cv2
import numpy as np

from . import assets

W, H = 1080, 1920
_det = None


def detector(size=(W, H), score=0.55):
    """YuNet nạp từ bộ nhớ (đường dẫn có dấu tiếng Việt trên Windows sẽ làm cv2 lỗi nếu nạp từ file)."""
    global _det
    if _det is None:
        p = assets.path("face_detection_yunet")
        if not os.path.exists(p):
            raise SystemExit("Thiếu model nhận diện mặt. Chạy trước:  python popedit.py setup")
        buf = np.frombuffer(open(p, "rb").read(), np.uint8)
        _det = cv2.FaceDetectorYN.create("onnx", buf, np.empty(0, np.uint8), size, score, 0.3, 5000)
    return _det


def detect(frame):
    """-> list [x, y, w, h, score] (toạ độ trên khung 1080x1920)."""
    h, w = frame.shape[:2]
    d = detector()
    d.setInputSize((w, h))
    _, f = d.detect(frame)
    if f is None:
        return []
    return [[float(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[-1])] for r in f]


def _iou(a, b):
    ix = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    iy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def clean(raw):
    """Bỏ nhận nhầm (bàn tay, hình nền): hộp quá nhỏ, và hộp điểm thấp không có hộp tin cậy cao ở khung lân cận."""
    out = []
    for i, boxes in enumerate(raw):
        keep = []
        for b in boxes:
            if b[2] < 50:
                continue
            if b[4] >= 0.8:
                keep.append(b)
                continue
            near = [x for j in range(max(0, i - 2), min(len(raw), i + 3)) for x in raw[j] if x[4] >= 0.85]
            if any(_iou(b, x) >= 0.2 for x in near):
                keep.append(b)
        out.append(keep)
    return out


def _bg_color_rows(fr, bgs):
    rgb = fr[:, :, ::-1].astype(np.int16)
    d = np.abs(rgb[:, :, None, :] - np.array(bgs)[None, None, :, :]).sum(3).min(2)
    return (d < 45).mean(1)


def seam_of(fr):
    """Tìm đường chia đôi (đồ họa nền phẳng phía trên, người nói phía dưới). Trả [y_seam, đáy_nội_dung] hoặc None."""
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dev = np.abs(g - np.median(g, axis=1, keepdims=True)).mean(1)
    edge = np.abs(g[4:] - g[:-4]).mean(1)
    best = None
    for y in range(840, 1010):
        if dev[y - 44:y - 3].max() >= 9.0:
            continue
        e = edge[y - 2]
        if e >= 9.0 and (best is None or e > best[1]):
            best = (y, e)
    if not best:
        return None
    y = best[0]
    busy = np.where(dev[200:y - 6] > 5.0)[0]
    return [int(y), int(busy.max() + 200) if len(busy) else 200]


def analyze(video, step=5, cache=None, verbose=True):
    """Quét video 6 mẫu/giây. Trả về dict(times, faces, seams). Lưu cache JSON nếu có."""
    if cache and os.path.exists(cache):
        d = json.load(open(cache))
        return d
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    times, raw, seams = [], [], []
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % step == 0:
            times.append(round(i / fps, 3))
            raw.append(detect(fr))
            seams.append(seam_of(fr))
            if verbose and len(times) % 100 == 0:
                print(f"  quét {i / fps:6.1f}s / {n / fps:.1f}s", flush=True)
        i += 1
    cap.release()
    d = dict(fps=fps, times=times, faces=clean(raw), seams=seams)
    if cache:
        json.dump(d, open(cache, "w"))
    return d
