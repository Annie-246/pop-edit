"""Lõi đồ họa: font, nền, thẻ, tiêu đề, sticker, danh sách pop-up, màn swipe, PiP, chuyển cảnh.

Mọi phần tử (element) có cùng giao diện:  draw(canvas_bgr, local_t, scene_dur)
- local_t: giây tính từ đầu cảnh
- canvas: ảnh BGR 1080x1920 đang dựng
Thời gian trong project.json là thời gian TUYỆT ĐỐI của video; timeline.py đổi sang local_t.
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import assets, theme as _theme

W, H = 1080, 1920
SPLIT_Y = 960                          # chiều cao vùng trên khi chia đôi
SBOX = (30, 235, 1020, 505)            # khung đặt minh họa trong vùng trên (x, y, w, h)

T = _theme.resolve(None)               # bảng màu hiện hành (set_theme đổi)
BG_LIGHT = BG_DARK = None


# ----------------------------------------------------------------------------- tiện ích chung
def ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def ease_back(p):
    p = max(0.0, min(1.0, p))
    c1 = 1.4
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


_font_cache = {}


def font(size, wght=400, italic=True):
    """italic + đậm -> Bricolage (tiêu đề) | italic nhẹ -> Plus Jakarta nghiêng | không italic -> Plus Jakarta."""
    k = (size, wght, italic)
    if k not in _font_cache:
        if italic and wght >= 700:
            f = ImageFont.truetype(assets.path("BricolageGrotesque"), size)
            f.set_variation_by_axes([96, 800, 100])
        elif italic:
            f = ImageFont.truetype(assets.path("PlusJakartaSans-Italic"), size)
            f.set_variation_by_axes([wght])
        else:
            f = ImageFont.truetype(assets.path("PlusJakartaSans.ttf"), size)
            f.set_variation_by_axes([wght])
        _font_cache[k] = f
    return _font_cache[k]


def to_bgra(pil):
    a = np.array(pil.convert("RGBA"))
    return a[:, :, [2, 1, 0, 3]].copy()


def blend(dst, src, x, y, opacity=1.0):
    """alpha-over ảnh BGRA lên BGR tại (x, y); tự cắt theo khung."""
    h, w = src.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = (s[:, :, 3:4].astype(np.float32) / 255.0) * opacity
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (d * (1 - a) + s[:, :, :3].astype(np.float32) * a).astype(np.uint8)


def paste_rgba(dst, src, x, y):
    """alpha-over BGRA lên BGRA (giữ kênh alpha)."""
    h, w = src.shape[:2]
    reg = dst[y:y + h, x:x + w]
    a = src[:, :, 3:4].astype(np.float32) / 255.0
    ra = reg[:, :, 3:4].astype(np.float32) / 255.0
    oa = a + ra * (1 - a)
    rgb = (src[:, :, :3] * a + reg[:, :, :3] * ra * (1 - a)) / np.maximum(oa, 1e-6)
    reg[:, :, :3] = rgb.astype(np.uint8)
    reg[:, :, 3] = (oa[:, :, 0] * 255).astype(np.uint8)


def scaled(img, s):
    if abs(s - 1) < 1e-3:
        return img
    h, w = img.shape[:2]
    return cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))),
                      interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)


def text_img(text, size, wght, italic, fill, stroke=0, stroke_fill=(0, 0, 0)):
    f = font(size, wght, italic)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = 12 + stroke
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=tuple(fill) + (255,),
                            stroke_width=stroke, stroke_fill=tuple(stroke_fill) + (255,))
    return to_bgra(im)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------- theme + nền
def _grid(bg, line, dot, step=96):
    img = np.full((H, W, 3), bg[::-1], np.uint8)
    for x in range(0, W, step):
        img[:, x:x + 2] = line[::-1]
    for y in range(0, H, step):
        img[y:y + 2, :] = line[::-1]
    for j, y in enumerate(range(0, H, step)):
        for i, x in enumerate(range(0, W, step)):
            if (i * 7 + j * 13) % 6 == 0:
                cv2.circle(img, (x + 1, y + 1), 5, dot[::-1], -1, cv2.LINE_AA)
    return img


def set_theme(spec):
    """Chọn bảng màu và dựng lại nền."""
    global T, BG_LIGHT, BG_DARK
    T = _theme.resolve(spec)
    BG_LIGHT = _grid(T["bg_light"], T["grid_light"], T["dot_light"])
    BG_DARK = _grid(T["bg_dark"], T["grid_dark"], T["dot_dark"])
    _font_cache.clear()
    return T


# ----------------------------------------------------------------------------- video + thẻ
class Clip:
    """Đọc tuần tự 1 video theo thời gian cục bộ (giây). Hết video thì đứng hình ở khung cuối."""

    def __init__(self, path, t0=0.0, crop=None):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise SystemExit(f"Không mở được: {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.t0, self.crop = t0, crop
        self.pos = int(round(t0 * self.fps)) - 1
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.pos + 1)
        self.last = None
        self.is_image = self.n <= 1

    def get(self, local_t):
        if self.is_image:
            if self.last is None:
                ok, self.last = self.cap.read()
            return self._crop(self.last)
        want = min(int(round((self.t0 + max(local_t, 0)) * self.fps)), self.n - 1)
        if want < self.pos or want - self.pos > 40:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, want)
            self.pos = want - 1
        while self.pos < want:
            ok, fr = self.cap.read()
            if not ok:
                break
            self.pos += 1
            self.last = fr
        fr = self.last if self.last is not None else np.zeros((H, W, 3), np.uint8)
        return self._crop(fr)

    def _crop(self, fr):
        if self.crop:
            x, y, w, h = self.crop
            fr = fr[y:y + h, x:x + w]
        return fr

    def release(self):
        self.cap.release()


def load_image(path):
    """Ảnh tĩnh -> BGR (cv2 không đọc được đường dẫn có dấu trên Windows bằng imread)."""
    data = np.fromfile(path, np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"Không đọc được ảnh: {path}")
    return img


class _Source:
    """Một nguồn hình (ảnh hoặc video) có crop + chế độ đứng hình."""

    def __init__(self, file, t0=0.0, crop=None, freeze=False):
        self.file, self.t0, self.crop, self.freeze = file, t0, crop, freeze
        self.clip = None
        self.still = None
        self.is_img = os.path.splitext(file)[1].lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    def frame(self, local_t):
        if self.is_img:
            if self.still is None:
                im = load_image(self.file)
                if self.crop:
                    x, y, w, h = self.crop
                    im = im[y:y + h, x:x + w]
                self.still = im
            return self.still
        if self.clip is None:
            self.clip = Clip(self.file, self.t0, self.crop)
        return self.clip.get(0 if self.freeze else local_t)

    def close(self):
        if self.clip:
            self.clip.release()


_mask_cache, _shadow_cache = {}, {}


def rounded_mask(w, h, r):
    k = (w, h, r)
    if k not in _mask_cache:
        m = Image.new("L", (w * 2, h * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=r * 2, fill=255)
        _mask_cache[k] = np.array(m.resize((w, h), Image.LANCZOS))
    return _mask_cache[k]


def shadow_for(w, h, r, pad=60):
    k = (w, h, r, tuple(T["shadow"]))
    if k not in _shadow_cache:
        im = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
        ImageDraw.Draw(im).rounded_rectangle([pad, pad + 22, pad + w, pad + h + 22], radius=r, fill=95)
        a = np.array(im.filter(ImageFilter.GaussianBlur(24)))
        arr = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8)
        arr[:, :, 3] = a
        arr[:, :, :3] = tuple(T["shadow"])[::-1]
        _shadow_cache[k] = arr
    return _shadow_cache[k]


def fit_size(sw, sh, bw, bh):
    s = min(bw / sw, bh / sh)
    return int(sw * s), int(sh * s)


def make_card(frame, box_w, box_h, radius=38, cover=False, border=8):
    """Khung bo góc có viền trắng + bóng đổ. Trả về (ảnh BGRA, pad)."""
    sh_, sw_ = frame.shape[:2]
    if cover:
        w, h = box_w, box_h
        s = max(w / sw_, h / sh_)
        rs = cv2.resize(frame, (int(sw_ * s) + 1, int(sh_ * s) + 1), interpolation=cv2.INTER_AREA)
        x0, y0 = (rs.shape[1] - w) // 2, (rs.shape[0] - h) // 2
        rs = rs[y0:y0 + h, x0:x0 + w]
    else:
        w, h = fit_size(sw_, sh_, box_w, box_h)
        rs = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA if w < sw_ else cv2.INTER_CUBIC)
    pad = 60
    canvas = shadow_for(w + 2 * border, h + 2 * border, radius + border).copy()
    white = np.full((h + 2 * border, w + 2 * border, 3), 255, np.uint8)
    white[border:border + h, border:border + w] = rs
    mask = rounded_mask(w + 2 * border, h + 2 * border, radius + border)
    paste_rgba(canvas, np.dstack([white, mask]), pad, pad)
    return canvas, pad


# ----------------------------------------------------------------------------- icon + sticker
def _heart_pts(cx, cy, r):
    pts = []
    for k in range(0, 360, 4):
        t = math.radians(k)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * r / 16, cy - y * r / 16))
    return pts


def _star_pts(cx, cy, r, n=5):
    pts = []
    for i in range(n * 2):
        a = -math.pi / 2 + i * math.pi / n
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


ICON_KINDS = ["health", "money", "love", "star", "bolt", "chat", "check", "target", "bulb", "book", "robot", "script"]
_PLATE = {"health": (255, 226, 232), "money": (255, 238, 205), "love": (255, 226, 238), "star": (255, 243, 205),
          "bolt": (255, 243, 205), "chat": (226, 238, 255), "check": (222, 245, 230), "target": (255, 228, 224),
          "bulb": (255, 243, 205), "book": (232, 232, 255), "robot": (255, 226, 238), "script": (255, 244, 230)}


def icon_img(kind, n=170, plate=True):
    """Icon vẽ bằng vector (không cần file ngoài). kind: xem ICON_KINDS."""
    S = 3
    N = n * S
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if plate:
        d.rounded_rectangle([0, 0, N - 1, N - 1], radius=int(N * 0.26), fill=_PLATE.get(kind, (255, 240, 244)) + (255,))
    c = N / 2
    red, pink, gold, ink = (226, 78, 110, 255), (250, 160, 190, 255), (246, 188, 50, 255), tuple(T["ink"]) + (255,)
    P = lambda x, y: (x * N / 100.0, y * N / 100.0)  # noqa: E731
    if kind == "health":
        d.polygon(_heart_pts(c, c + N * 0.03, N * 0.30), fill=red)
        w = N * 0.065
        d.rectangle([c - w, c - N * 0.17, c + w, c + N * 0.17], fill=(255, 255, 255, 255))
        d.rectangle([c - N * 0.17, c - w, c + N * 0.17, c + w], fill=(255, 255, 255, 255))
    elif kind == "money":
        d.ellipse([c - N * 0.31, c - N * 0.31, c + N * 0.31, c + N * 0.31], fill=gold, outline=(190, 120, 20, 255), width=int(N * 0.03))
        d.ellipse([c - N * 0.23, c - N * 0.23, c + N * 0.23, c + N * 0.23], outline=(255, 226, 130, 255), width=int(N * 0.02))
        f = font(int(N * 0.36), 800, True)
        bb = f.getbbox("$")
        d.text((c - (bb[0] + bb[2]) / 2, c - (bb[1] + bb[3]) / 2), "$", font=f, fill=(150, 90, 10, 255))
    elif kind == "love":
        d.polygon(_heart_pts(c - N * 0.10, c + N * 0.02, N * 0.22), fill=red)
        d.polygon(_heart_pts(c + N * 0.12, c - N * 0.04, N * 0.19), fill=pink, outline=(255, 255, 255, 255))
    elif kind == "star":
        d.polygon(_star_pts(c, c + N * 0.02, N * 0.33), fill=gold, outline=(190, 120, 20, 255))
    elif kind == "bolt":
        d.polygon([P(56, 12), P(30, 54), P(48, 54), P(40, 88), P(70, 42), P(52, 42)], fill=gold, outline=(190, 120, 20, 255))
    elif kind == "chat":
        d.rounded_rectangle([*P(18, 22), *P(82, 66)], radius=int(N * 0.1), fill=(70, 130, 240, 255))
        d.polygon([P(32, 64), P(30, 82), P(48, 64)], fill=(70, 130, 240, 255))
        for x in (36, 50, 64):
            d.ellipse([*P(x - 3.5, 40), *P(x + 3.5, 47)], fill=(255, 255, 255, 255))
    elif kind == "check":
        d.ellipse([*P(16, 16), *P(84, 84)], fill=(60, 180, 110, 255))
        d.line([P(32, 52), P(44, 64), P(68, 36)], fill=(255, 255, 255, 255), width=int(N * 0.08), joint="curve")
    elif kind == "target":
        for r, col in ((34, red), (24, (255, 255, 255, 255)), (14, red), (5, (255, 255, 255, 255))):
            d.ellipse([c - N * r / 100, c - N * r / 100, c + N * r / 100, c + N * r / 100], fill=col)
    elif kind == "bulb":
        d.ellipse([*P(26, 14), *P(74, 62)], fill=gold, outline=(190, 120, 20, 255), width=int(N * 0.02))
        d.polygon([P(38, 56), P(62, 56), P(58, 72), P(42, 72)], fill=gold)
        d.rounded_rectangle([*P(40, 74), *P(60, 84)], radius=int(N * 0.03), fill=(150, 150, 160, 255))
    elif kind == "book":
        d.rounded_rectangle([*P(18, 22), *P(50, 78)], radius=int(N * 0.03), fill=(110, 90, 220, 255))
        d.rounded_rectangle([*P(50, 22), *P(82, 78)], radius=int(N * 0.03), fill=(150, 130, 240, 255))
        for y in (36, 48, 60):
            d.line([P(58, y), P(75, y)], fill=(255, 255, 255, 255), width=int(N * 0.02))
    elif kind == "robot":
        rose, deep = tuple(T["accent"]) + (255,), tuple(T["deep"]) + (255,)
        d.line([P(50, 16), P(50, 26)], fill=deep, width=int(N * 0.03))
        d.ellipse([*P(45, 8), *P(55, 18)], fill=rose)
        d.rounded_rectangle([*P(22, 26), *P(78, 72)], radius=int(N * 0.12), fill=pink, outline=deep, width=int(N * 0.024))
        d.rounded_rectangle([*P(14, 40), *P(22, 58)], radius=int(N * 0.03), fill=rose)
        d.rounded_rectangle([*P(78, 40), *P(86, 58)], radius=int(N * 0.03), fill=rose)
        for cx in (38, 62):
            d.ellipse([*P(cx - 7, 38), *P(cx + 7, 52)], fill=(255, 255, 255, 255), outline=deep, width=int(N * 0.018))
            d.ellipse([*P(cx - 3, 42), *P(cx + 3, 49)], fill=deep)
        d.arc([*P(38, 52), *P(62, 68)], 20, 160, fill=deep, width=int(N * 0.024))
        d.rounded_rectangle([*P(34, 76), *P(66, 88)], radius=int(N * 0.05), fill=rose)
    elif kind == "script":
        deep = tuple(T["accent"]) + (255,)
        d.rounded_rectangle([*P(24, 14), *P(70, 86)], radius=int(N * 0.05), fill=(255, 255, 255, 255), outline=deep, width=int(N * 0.024))
        for i, w in enumerate((38, 34, 38, 26)):
            y = 28 + i * 12
            d.rounded_rectangle([*P(31, y), *P(31 + w, y + 4)], radius=int(N * 0.02), fill=pink)
        d.polygon([P(66, 58), P(88, 36), P(94, 42), P(72, 64)], fill=(250, 200, 90, 255), outline=deep)
        d.polygon([P(66, 58), P(72, 64), P(62, 68)], fill=deep)
    else:
        d.polygon(_star_pts(c, c, N * 0.33), fill=gold)
    return im.resize((n, n), Image.LANCZOS)


class Sticker:
    """Sticker vẽ sẵn (xem ICON_KINDS) bật lên có nghiêng nhẹ."""

    def __init__(self, kind, cx, cy, size, start=0.3, tilt=-8, **_):
        self.kind, self.cx, self.cy, self.size, self.start, self.tilt = kind, cx, cy, size, start, tilt
        pad = 40
        n = size
        base = Image.new("RGBA", (n + 2 * pad, n + 2 * pad), (0, 0, 0, 0))
        sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 12, pad + n, pad + n + 12], radius=34, fill=tuple(T["shadow"]) + (90,))
        base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        ImageDraw.Draw(base).rounded_rectangle([pad, pad, pad + n, pad + n], radius=34, fill=tuple(T["plate"]) + (255,),
                                               outline=(255, 255, 255, 255), width=3)
        base.alpha_composite(icon_img(kind, int(n * 0.84), plate=False), (pad + int(n * 0.08), pad + int(n * 0.08)))
        self.img = to_bgra(base)
        self.end = None

    def draw(self, canvas, lt, scene_dur):
        local = lt - self.start
        if local <= 0:
            return
        e = ease_back(local / 0.55)
        fade = ease(local / 0.2)
        wob = math.sin(local * 2.2) * 2.0
        M_ = cv2.getRotationMatrix2D((self.img.shape[1] / 2, self.img.shape[0] / 2), self.tilt + wob, 0.6 + 0.4 * e)
        h, w = self.img.shape[:2]
        rot = cv2.warpAffine(self.img, M_, (w, h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        blend(canvas, rot, int(self.cx - w / 2), int(self.cy - h / 2 + (1 - ease(local / 0.5)) * 30), fade)


# ----------------------------------------------------------------------------- tiêu đề
def key_img(text, size, dark, hl):
    """Chữ tiêu đề đậm viết hoa; hl=True thì có ô chọn chữ (selection) với 2 tay cầm."""
    f = font(size, 800, True)
    l, t, r, b = f.getbbox(text)
    pad = 34
    w, h = r - l + 2 * pad, b - t + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tx, ty = pad - l, pad - t
    acc = tuple(T["accent"]) + (255,)
    if hl:
        hb0, hb1 = f.getbbox("H")[1], f.getbbox("H")[3]
        x0, x1 = pad - 16, w - pad + 16
        y0, y1 = ty + hb0 - 10, ty + hb1 + 10
        d.rectangle([x0, y0, x1, y1], fill=tuple(T["sel"] if dark else T["sel_dark"]) + (170,))
        d.rectangle([x0 - 2, y0, x0 + 1, y1], fill=acc)
        d.rectangle([x1 - 1, y0, x1 + 2, y1], fill=acc)
        d.ellipse([x0 - 11, y0 - 11, x0 + 11, y0 + 11], fill=acc)
        d.ellipse([x1 - 11, y1 - 11, x1 + 11, y1 + 11], fill=acc)
    d.text((tx, ty), text, font=f, fill=tuple(T["ink"]) + (255,))
    return to_bgra(im), pad


class Title:
    """lines: [["lead"|"key"|"small", "chữ"], ...] xếp giữa, hiện lần lượt. Dòng key cuối có ô chọn chữ."""

    def __init__(self, lines, y=130, start=0.0, end=None, key_size=118, lead_size=64, dark=True, gap=6,
                 compact=False, **_):
        if compact:
            key_size, lead_size, y = int(key_size * 0.76), int(lead_size * 0.8), 40
        key_size, lead_size = int(key_size * 1.28), int(lead_size * 0.95)
        self.start, self.end, self.y = start, end, y
        self.imgs = []
        keys = [i for i, ln in enumerate(lines) if ln[0] not in ("lead", "small")]
        last_key = max(keys) if keys else -1
        for i, (kind, text) in enumerate(lines):
            if kind == "lead":
                img, pad = text_img(text, lead_size, 400, True, T["lead_light"] if dark else T["lead_dark"]), 12
            elif kind == "small":
                img, pad = text_img(text, int(lead_size * 0.7), 400, True, T["small_light"] if dark else T["lead_dark"]), 12
            else:
                img, pad = key_img(text.upper(), key_size, dark, i == last_key)
            if img.shape[1] > W - 60:
                s = (W - 60) / img.shape[1]
                img, pad = scaled(img, s), int(pad * s)
            step = img.shape[0] - 2 * pad + (10 if kind in ("lead", "small") else 16) + gap
            self.imgs.append((img, pad, step))

    def draw(self, canvas, lt, scene_dur):
        if lt < self.start or (self.end is not None and lt > self.end):
            return
        y = self.y
        for i, (img, pad, step) in enumerate(self.imgs):
            p = ease((lt - self.start - i * 0.12) / 0.5)
            h, w = img.shape[:2]
            if p > 0:
                blend(canvas, img, (W - w) // 2, int(y - pad + (1 - p) * 56), p)
            y += step


# ----------------------------------------------------------------------------- thẻ minh họa
class Media(_Source):
    """Thẻ minh họa (ảnh hoặc video) bật vào có phóng nhẹ. show=[a,b] là giây cục bộ."""

    def __init__(self, file, show, box=(40, 440, 1000, 920), t0=0.0, crop=None, tag=None, cover=False, ken=0.03,
                 dark=True, freeze=False, **_):
        super().__init__(file, t0, crop, freeze)
        self.start, self.end = show
        self.box, self.tag, self.cover, self.ken = box, tag, cover, ken
        self._tag_img = text_img(tag, 30, 400, True, T["small_light"] if dark else T["lead_dark"]) if tag else None

    def draw(self, canvas, lt, scene_dur):
        if lt < self.start or lt > self.end:
            return
        frame = self.frame(lt - self.start)
        bx, by, bw, bh = self.box
        card, pad = make_card(frame, bw, bh, cover=self.cover)
        local = lt - self.start
        e = ease_back(local / 0.45)
        fade = ease(local / 0.25)
        out = ease((self.end - lt) / 0.15) if self.end - lt < 0.15 else 1.0
        s = (0.9 + 0.1 * e) * (1 + self.ken * (local / max(self.end - self.start, 0.1)))
        cs = scaled(card, s)
        h2, w2 = cs.shape[:2]
        cx, cy = bx + bw // 2, by + bh // 2 + int((1 - ease(local / 0.45)) * 40)
        blend(canvas, cs, cx - w2 // 2, cy - h2 // 2, fade * out)
        if self._tag_img is not None:
            card_h = h2 - 2 * int(pad * s)
            blend(canvas, self._tag_img, cx - self._tag_img.shape[1] // 2, cy + card_h // 2 + 8, fade * out)


class Cards:
    """Hàng thẻ chân dung (2-4 thẻ) bật lên lần lượt, có tên + phụ đề dưới mỗi thẻ."""

    def __init__(self, items, y=640, start=0.0, stagger=0.45, size=(310, 430), **_):
        self.start, self.stagger, self.size, self.y = start, stagger, size, y
        self.cards = []
        for it in items:
            src = _Source(it["file"], it.get("t0", 0), it.get("crop"), True)
            fr = src.frame(0)
            src.close()
            card, pad = make_card(fr, size[0], size[1], radius=30, cover=True)
            name = text_img(it["name"], 44, 800, True, T["ink"]) if it.get("name") else None
            sub = text_img(it["sub"], 32, 400, True, T["small_light"]) if it.get("sub") else None
            self.cards.append((card, pad, name, sub))
        self.end = None

    def draw(self, canvas, lt, scene_dur):
        n = len(self.cards)
        gap = 26
        x0 = (W - (n * self.size[0] + (n - 1) * gap)) // 2
        for i, (card, pad, name, sub) in enumerate(self.cards):
            local = lt - self.start - i * self.stagger
            if local <= 0:
                continue
            e, fade = ease_back(local / 0.5), ease(local / 0.3)
            cs = scaled(card, 0.85 + 0.15 * e)
            h2, w2 = cs.shape[:2]
            cx = x0 + i * (self.size[0] + gap) + self.size[0] // 2
            cy = self.y + self.size[1] // 2 + int((1 - ease(local / 0.5)) * 60)
            blend(canvas, cs, cx - w2 // 2, cy - h2 // 2, fade)
            if name is not None:
                blend(canvas, name, cx - name.shape[1] // 2, self.y + self.size[1] + 22, fade)
                if sub is not None:
                    blend(canvas, sub, cx - sub.shape[1] // 2, self.y + self.size[1] + 22 + name.shape[0] - 12, fade)


class Counter:
    """Số đếm lên (vd $276). prefix/suffix tuỳ ý, decimals để lấy số lẻ."""

    def __init__(self, value, prefix="", suffix="", y=640, start=0.0, dur=1.2, size=330, dark=False, decimals=0, **_):
        self.value, self.prefix, self.suffix, self.y, self.start, self.dur = value, prefix, suffix, y, start, dur
        self.size, self.dark, self.decimals = size, dark, decimals
        self.cache = {}
        self.end = None

    def draw(self, canvas, lt, scene_dur):
        if lt < self.start:
            return
        v = self.value * ease((lt - self.start) / self.dur)
        txt = f"{self.prefix}{v:,.{self.decimals}f}{self.suffix}"
        if txt not in self.cache:
            self.cache[txt] = text_img(txt, self.size, 900, True, T["accent"] if self.dark else T["deep"])
        img = self.cache[txt]
        if img.shape[1] > W - 60:
            img = scaled(img, (W - 60) / img.shape[1])
        blend(canvas, img, (W - img.shape[1]) // 2, self.y, ease((lt - self.start) / 0.25))


class Logo:
    """Logo PNG (nền trong) bật vào giữa khung."""

    def __init__(self, file, y=900, width=900, start=0.0, **_):
        im = Image.open(file).convert("RGBA")
        arr = to_bgra(im)
        h = int(arr.shape[0] * width / arr.shape[1])
        self.img = cv2.resize(arr, (width, h), interpolation=cv2.INTER_AREA)
        self.y, self.start, self.end = y, start, None

    def draw(self, canvas, lt, scene_dur):
        if lt < self.start:
            return
        local = lt - self.start
        im = scaled(self.img, 0.8 + 0.2 * ease_back(local / 0.55))
        h, w = im.shape[:2]
        blend(canvas, im, (W - w) // 2, self.y - h // 2 + int((1 - ease(local / 0.5)) * 40), ease(local / 0.3))


class CardList:
    """Danh sách thẻ xếp dọc (icon + nhãn + từ khoá) bật lên đúng lúc nói. times = giây cục bộ cho từng thẻ."""

    def __init__(self, items, times, hide_at=None, y=450, card_h=235, gap=26, **_):
        self.starts, self.end = list(times), hide_at
        self.y0, self.card_h, self.gap = y, card_h, gap
        self.cards = []
        cw, pad = 1000, 50
        for it in items:
            label, chips, kind = it["label"], it.get("chips", []), it.get("icon", "star")
            base = Image.new("RGBA", (cw + 2 * pad, card_h + 2 * pad), (0, 0, 0, 0))
            sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 14, pad + cw, pad + card_h + 14], radius=40, fill=tuple(T["shadow"]) + (80,))
            base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
            d = ImageDraw.Draw(base)
            d.rounded_rectangle([pad, pad, pad + cw, pad + card_h], radius=40, fill=tuple(T["plate"]) + (255,), outline=(255, 255, 255, 255), width=4)
            base.alpha_composite(icon_img(kind, 170), (pad + 32, pad + (card_h - 170) // 2))
            d.text((pad + 240, pad + 34), label.upper(), font=font(70, 800, True), fill=tuple(T["ink"]) + (255,))
            chip_im = Image.new("RGBA", base.size, (0, 0, 0, 0))
            cd = ImageDraw.Draw(chip_im)
            cf = font(34, 400, True)
            x = pad + 240
            for ch in chips:
                tw = cd.textlength(ch, font=cf)
                cd.rounded_rectangle([x, pad + 140, x + tw + 40, pad + 196], radius=28, fill=tuple(T["sel_dark"]) + (255,),
                                     outline=tuple(T["sel"]) + (255,), width=2)
                cd.text((x + 20, pad + 147), ch, font=cf, fill=tuple(T["accent"]) + (255,))
                x += tw + 54
            self.cards.append((to_bgra(base), to_bgra(chip_im), pad))

    def draw(self, canvas, lt, scene_dur):
        out = 1.0
        if self.end is not None and self.end - lt < 0.2:
            out = ease((self.end - lt) / 0.2)
        if out <= 0:
            return
        x0 = (W - 1000) // 2 - 50
        for i, (base, chips, pad) in enumerate(self.cards):
            local = lt - self.starts[i]
            if local <= 0:
                continue
            cs = scaled(base, 0.82 + 0.18 * ease_back(local / 0.5))
            h2, w2 = cs.shape[:2]
            cx = x0 + base.shape[1] // 2
            cy = self.y0 - pad + base.shape[0] // 2 + i * (self.card_h + self.gap) + int((1 - ease(local / 0.45)) * 50)
            blend(canvas, cs, cx - w2 // 2, cy - h2 // 2, ease(local / 0.2) * out)
            cl = local - 0.22
            if cl > 0:
                c2 = scaled(chips, 0.82 + 0.18 * ease_back(cl / 0.4))
                h3, w3 = c2.shape[:2]
                blend(canvas, c2, cx - w3 // 2, cy - h3 // 2, ease(cl / 0.25) * out)


class Slides:
    """Mỗi mục chiếm FULL khung hình; mục kế tiếp swipe từ phải sang. items: file, t0, crop, name, sub."""

    def __init__(self, items, slot, swipe=0.38, header=None, **_):
        self.items, self.slot, self.swipe = items, slot, swipe
        self.srcs = [_Source(it["file"], it.get("t0", 0), it.get("crop"), it.get("freeze", False)) for it in items]
        self.names = []
        for it in items:
            nm = key_img(it["name"].upper(), 120, True, True)[0] if it.get("name") else None
            sub = text_img(it["sub"], 40, 400, True, T["lead_dark"]) if it.get("sub") else None
            self.names.append((nm, sub))
        self.header = text_img(header, 38, 400, True, T["lead_dark"]) if header else None
        self.end = None

    def _frame(self, i, local):
        fr = self.srcs[i].frame(local)
        h0, w0 = fr.shape[:2]
        s = max(W / w0, H / h0)
        rs = cv2.resize(fr, (int(w0 * s) + 1, int(h0 * s) + 1), interpolation=cv2.INTER_CUBIC)
        x0, y0 = (rs.shape[1] - W) // 2, (rs.shape[0] - H) // 2
        out = rs[y0:y0 + H, x0:x0 + W].copy()
        g = np.linspace(0.45, 0, 420)[:, None, None]
        out[:420] = (out[:420] * (1 - g) + np.array(T["cream"][::-1]) * g).astype(np.uint8)
        nm, sub = self.names[i]
        if nm is not None:
            blend(out, nm, 50, 120)
            if sub is not None:
                blend(out, sub, 70, 120 + nm.shape[0] - 6)
        return out

    def draw(self, canvas, lt, scene_dur):
        n = len(self.items)
        idx = min(int(lt // self.slot), n - 1)
        local = lt - idx * self.slot
        cur = self._frame(idx, local)
        if idx > 0 and local < self.swipe:
            p = ease(local / self.swipe)
            prev = self._frame(idx - 1, self.slot + local)
            off = int(W * p)
            canvas[:, :W - off] = prev[:, off:]
            canvas[:, W - off:] = cur[:, :off]
            x = W - off
            if 0 < x < W:
                canvas[:, max(x - 5, 0):x] = (np.array(T["spike"][::-1]) * 0.9).astype(np.uint8)
        else:
            canvas[:] = cur
        if self.header is not None:
            blend(canvas, self.header, 50, 70)

    def close(self):
        for s in self.srcs:
            s.close()


# ----------------------------------------------------------------------------- cảnh + bố cục
class Scene:
    """layout: person | full | split | pip.   bg: light | dark (chỉ cho full/split/pip)."""

    def __init__(self, t0, t1, layout="full", bg="light", elems=(), pip=None, split_crop_y=130, sub_style=None):
        self.t0, self.t1, self.layout, self.bg = t0, t1, layout, bg
        self.elems = list(elems)
        self.pip = pip or {}
        self.split_crop_y = split_crop_y
        self.sub_style = sub_style          # None | "person": ép phụ đề kiểu chữ trắng viền (khi nền là video)
        self._pip_cache = {}

    @property
    def is_person(self):
        return self.layout == "person"

    @property
    def split(self):
        return self.layout == "split"

    def render(self, canvas, t, person_frame):
        lt, dur = t - self.t0, self.t1 - self.t0
        if self.is_person:
            canvas[:] = person_frame
        else:
            canvas[:] = BG_DARK if self.bg == "dark" else BG_LIGHT
        if self.split:
            canvas[SPLIT_Y:] = person_frame[self.split_crop_y:self.split_crop_y + (H - SPLIT_Y)]
            bar = T["spike"][::-1] if self.bg == "dark" else T["accent"][::-1]
            canvas[SPLIT_Y - 6:SPLIT_Y] = bar
            g = np.linspace(0.35, 0, 26)[:, None, None]
            canvas[SPLIT_Y:SPLIT_Y + 26] = (canvas[SPLIT_Y:SPLIT_Y + 26] * (1 - g)).astype(np.uint8)
        for el in self.elems:
            el.draw(canvas, lt, dur)
        if self.layout == "pip":
            self._draw_pip(canvas, lt, person_frame)

    def _draw_pip(self, canvas, lt, person_frame):
        """Người nói thu nhỏ ở góc/đáy, phủ lên đồ họa hoặc clip toàn màn hình."""
        p = self.pip
        w = int(p.get("w", 400))
        h = int(p.get("h", w * 1.15))
        pos = p.get("pos", "bottom-right")
        crop = p.get("crop") or [90, 60, 900, int(900 * h / w)]     # vùng cắt trên khung nguồn
        x, y, cw, ch = crop
        fr = person_frame[y:y + ch, x:x + cw]
        circle = p.get("shape", "rounded") == "circle"
        key = (w, h, circle)
        r = min(w, h) // 2 if circle else int(p.get("radius", 34))
        card, pad = make_card(fr, w, h, radius=r, cover=True)
        margin = int(p.get("margin", 36))
        px = {"bottom-right": W - w - margin, "bottom-left": margin, "bottom-center": (W - w) // 2}.get(pos, W - w - margin)
        py = H - h - int(p.get("bottom", 150)) if pos.startswith("bottom") else margin + 120
        e = ease_back(lt / 0.45)
        cs = scaled(card, 0.8 + 0.2 * e)
        h2, w2 = cs.shape[:2]
        blend(canvas, cs, px - pad + (card.shape[1] - w2) // 2, py - pad + (card.shape[0] - h2) // 2, ease(lt / 0.2))

    def close(self):
        for el in self.elems:
            if hasattr(el, "close"):
                el.close()
            elif hasattr(el, "release"):
                el.release()


# ----------------------------------------------------------------------------- chuyển cảnh
def wipe(canvas, t, T0, half=0.22):
    """Tấm màu quét ngang phủ kín tại T0 rồi mở ra; nội dung đổi đúng lúc phủ kín."""
    p = (t - (T0 - half)) / (2 * half)
    if p <= 0 or p >= 1:
        return
    skew = 170
    xr = -skew + (W + 2 * skew) * min(p * 2, 1)
    xl = -skew + (W + 2 * skew) * max(p * 2 - 1, 0)
    pts = np.array([[xl, 0], [xr, 0], [xr - skew, H], [xl - skew, H]], np.int32)
    cv2.fillPoly(canvas, [pts], tuple(T["wipe"])[::-1], lineType=cv2.LINE_AA)
    lead = np.array([[xr - 14, 0], [xr, 0], [xr - skew, H], [xr - skew - 14, H]], np.int32)
    cv2.fillPoly(canvas, [lead], tuple(T["cream"])[::-1], lineType=cv2.LINE_AA)


set_theme(None)
