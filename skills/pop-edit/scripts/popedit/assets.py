"""Tài nguyên tải về lần đầu (font + model nhận diện mặt). Lưu ở ~/.popedit để mọi dự án dùng chung."""
import os
import sys
import urllib.request

HOME = os.environ.get("POPEDIT_HOME") or os.path.join(os.path.expanduser("~"), ".popedit")
FONT_DIR = os.path.join(HOME, "fonts")
MODEL_DIR = os.path.join(HOME, "models")

# (tên file lưu, URL) - tất cả đều là giấy phép mở (OFL / MIT)
FILES = [
    (os.path.join(FONT_DIR, "BricolageGrotesque.ttf"),
     "https://github.com/google/fonts/raw/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf"),
    (os.path.join(FONT_DIR, "PlusJakartaSans.ttf"),
     "https://github.com/google/fonts/raw/main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf"),
    (os.path.join(FONT_DIR, "PlusJakartaSans-Italic.ttf"),
     "https://github.com/google/fonts/raw/main/ofl/plusjakartasans/PlusJakartaSans-Italic%5Bwght%5D.ttf"),
    (os.path.join(MODEL_DIR, "face_detection_yunet_2023mar.onnx"),
     "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"),
]


def path(name):
    for p, _ in FILES:
        if os.path.basename(p).lower().startswith(name.lower()):
            return p
    raise KeyError(name)


def missing():
    return [(p, u) for p, u in FILES if not (os.path.exists(p) and os.path.getsize(p) > 10_000)]


def ensure(verbose=True):
    """Tải các file còn thiếu. Trả về True nếu đủ."""
    for p, url in missing():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if verbose:
            print(f"  tải {os.path.basename(p)} ...", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "popedit"})
            with urllib.request.urlopen(req, timeout=60) as r, open(p, "wb") as f:
                f.write(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"  LỖI tải {url}: {e}", file=sys.stderr)
    return not missing()
