"""Đọc project.json -> danh sách Scene. Mọi thời gian trong JSON là GIÂY TUYỆT ĐỐI của video."""
import json
import os

import cv2

from . import engine as E

ELEMENT_TYPES = ["title", "media", "counter", "logo", "sticker", "cards", "card_list", "slides"]


class Project:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.cfg = json.load(open(self.path, encoding="utf-8"))
        self.source = self.abs(self.cfg["source"])
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise SystemExit(f"Không mở được video nguồn: {self.source}")
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30
        self.duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
        if int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) != 1080 or int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) != 1920:
            print("CẢNH BÁO: nguồn không phải 1080x1920. Hãy đổi trước: ffmpeg -i in.mp4 -vf scale=1080:1920 out.mp4")
        cap.release()
        self.out = self.abs(self.cfg.get("out", "out/final.mp4"))
        self.audio = self.cfg.get("audio", {})
        E.set_theme(self.cfg.get("theme"))

    def abs(self, p):
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(self.dir, p))

    # ---- scene boundaries
    def raw_scenes(self):
        sc = sorted(self.cfg["scenes"], key=lambda s: s["t"][0])
        out, cur = [], 0.0
        for s in sc:
            a, b = float(s["t"][0]), float(s["t"][1])
            if a > cur + 1e-3:                                         # khoảng trống -> cảnh người nói
                out.append({"t": [cur, a], "layout": "person"})
            out.append(dict(s, t=[a, b]))
            cur = b
        if cur < self.duration - 1e-3:
            out.append({"t": [cur, self.duration + 0.2], "layout": "person"})
        else:
            out[-1]["t"][1] = max(out[-1]["t"][1], self.duration + 0.2)
        return out

    def build(self, boundaries=None):
        """boundaries: dict {chỉ số cảnh: thời điểm đầu cảnh mới} (sau khi khớp nhịp). Trả về list Scene."""
        raws = self.raw_scenes()
        if boundaries:
            for i, t in boundaries.items():
                raws[i]["t"][0] = t
                raws[i - 1]["t"][1] = t
        scenes = []
        for raw in raws:
            scenes.append(self._scene(raw))
        return scenes

    def _scene(self, raw):
        a, b = raw["t"]
        layout = raw.get("layout", "full")
        bg = raw.get("bg", "light")
        elems = [self._element(e, a, b, layout, bg) for e in raw.get("elements", [])]
        return E.Scene(a, b, layout, bg, elems, pip=raw.get("pip"),
                       split_crop_y=self.cfg.get("split_crop_y", 130), sub_style=raw.get("sub_style"))

    def _element(self, e, a, b, layout, bg):
        typ = e["type"]
        dark = bg != "dark"                       # dark=True nghĩa là NỀN SÁNG (chữ tối)
        compact = layout == "split"
        f = lambda p: self.abs(p)  # noqa: E731
        rel = lambda t: float(t) - a  # noqa: E731
        if typ == "title":
            show = e.get("show")
            return E.Title(e["lines"], y=e.get("y", 130), start=rel(show[0]) if show else 0.0,
                           end=rel(show[1]) if show else None, key_size=e.get("key_size", 118),
                           lead_size=e.get("lead_size", 64), dark=dark, compact=compact)
        if typ == "media":
            box = E.SBOX if compact else tuple(e.get("box", (40, 440, 1000, 920)))
            show = e.get("show", [a, b])
            return E.Media(f(e["file"]), (rel(show[0]), rel(show[1])), box=box, t0=e.get("t0", 0.0), crop=e.get("crop"),
                           tag=e.get("tag"), cover=e.get("cover", False), ken=e.get("ken", 0.03), dark=dark,
                           freeze=e.get("freeze", e.get("file", "").lower().endswith((".png", ".jpg", ".jpeg", ".webp"))))
        if typ == "counter":
            return E.Counter(e["value"], e.get("prefix", ""), e.get("suffix", ""), y=e.get("y", 640), start=rel(e.get("at", a)),
                             dur=e.get("dur", 1.2), size=e.get("size", 330), dark=dark, decimals=e.get("decimals", 0))
        if typ == "logo":
            return E.Logo(f(e["file"]), y=e.get("y", 900), width=e.get("width", 900), start=rel(e.get("at", a)))
        if typ == "sticker":
            return E.Sticker(e["kind"], e.get("x", 880), e.get("y", 1420), e.get("size", 200), start=rel(e.get("at", a)),
                             tilt=e.get("tilt", -8))
        if typ == "cards":
            items = [dict(it, file=f(it["file"])) for it in e["items"]]
            return E.Cards(items, y=e.get("y", 640), start=rel(e.get("at", a)), stagger=e.get("stagger", 0.45))
        if typ == "card_list":
            return E.CardList(e["items"], [rel(t) for t in e["times"]], hide_at=rel(e["hide_at"]) if "hide_at" in e else None,
                              y=e.get("y", 450))
        if typ == "slides":
            items = [dict(it, file=f(it["file"])) for it in e["items"]]
            return E.Slides(items, slot=(b - a) / len(items), header=e.get("header"))
        raise SystemExit(f"Loại phần tử không có: '{typ}'. Có: {', '.join(ELEMENT_TYPES)}")
