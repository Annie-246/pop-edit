"""Caption (phụ đề) cho video 9:16 bất kỳ: bóc băng -> (Claude sửa chữ) -> đặt vị trí né mặt -> in vào video.

Quy trình:
  1) transcribe  : tạo captions.draft.json  [{start, end, text}]  (start/end = lúc nói chữ đầu/chữ cuối của câu)
  2) Claude đọc draft, SỬA lỗi nghe nhầm (tên riêng, thuật ngữ), lưu thành captions.json
  3) burn        : đặt vị trí từng cụm chữ sao cho không chạm mặt, rồi in vào video
"""
import json
import os
import subprocess

import cv2
import numpy as np

from . import audio, engine as E, faces as F

W, H = 1080, 1920
SIZE = 58


# ----------------------------------------------------------------------------- 1) bóc băng
def transcribe(video, out_json, lang="vi", model="medium", prompt=None):
    from faster_whisper import WhisperModel
    wav = out_json + ".wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, language=lang, word_timestamps=True, vad_filter=True, beam_size=5, initial_prompt=prompt)
    out = []
    for s in segs:
        if s.words:
            out.append(dict(start=round(s.words[0].start, 2), end=round(s.words[-1].end, 2), text=s.text.strip()))
    os.remove(wav)
    json.dump(out, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


# ----------------------------------------------------------------------------- 2) cụm chữ
def chunks_from_segments(segs, max_words=6):
    out = []
    for sg in segs:
        a, b, words = float(sg["start"]), float(sg["end"]), sg["text"].split()
        if not words:
            continue
        n = max(1, int(np.ceil(len(words) / max_words)))
        per, i, parts = len(words) / n, 0, []
        for k in range(n):
            j = len(words) if k == n - 1 else int(round((k + 1) * per))
            parts.append(" ".join(words[i:j]))
            i = j
        tot = sum(len(p) for p in parts)
        t = a
        for p in parts:
            d = (b - a) * len(p) / tot
            out.append([t, t + d, p])
            t += d
    for k in range(len(out) - 1):                       # lấp khe nhỏ để chữ không nháy
        if 0 < out[k + 1][0] - out[k][1] < 0.25:
            out[k][1] = out[k + 1][0]
    return out


_cache = {}


def cap_img(text, maxw=920, size=SIZE):
    k = (text, maxw, size, tuple(E.T["sub_stroke"]))
    if k not in _cache:
        lines = E.wrap(text, E.font(size, 800, False), maxw)
        imgs = [E.text_img(ln, size, 800, False, (255, 255, 255), stroke=7, stroke_fill=E.T["sub_stroke"]) for ln in lines]
        hh = sum(i.shape[0] - 20 for i in imgs) + 20
        ww = max(i.shape[1] for i in imgs)
        out = np.zeros((hh, ww, 4), np.uint8)
        y = 0
        for i in imgs:
            E.paste_rgba(out, i, (ww - i.shape[1]) // 2, y)
            y += i.shape[0] - 20
        _cache[k] = out
    return _cache[k]


def _overlap(rect, boxes, grow=34):
    x0, y0, x1, y1 = rect
    area = 0
    for (x, y, w, h, s) in boxes:
        ix = min(x1, x + w + grow) - max(x0, x - grow)
        iy = min(y1, y + h + grow) - max(y0, y - grow)
        if ix > 0 and iy > 0:
            area += ix * iy
    return area


# ----------------------------------------------------------------------------- 3) đặt vị trí
def _split_states(times, faces, seams):
    """Mỗi mẫu: y_seam nếu là bố cục chia đôi (đồ họa trên, người dưới), ngược lại None."""
    st = []
    for bx, sm in zip(faces, seams):
        y = sm[0] if sm else None
        by_seam = y is not None and any(b[1] >= y - 60 for b in bx)
        by_face = any(b[1] >= 1000 and b[2] >= 300 and 380 <= b[0] + b[2] / 2 <= 700 for b in bx)
        st.append((y if y else -1) if (by_seam or by_face) else None)
    known = [(t, v) for t, v in zip(times, st) if v and v > 0]
    out = []
    for t, v in zip(times, st):
        if v is None:
            out.append(None)
        elif v > 0:
            out.append(v)
        else:
            near = [kv for kv in known if abs(kv[0] - t) <= 1.5]
            out.append(min(near, key=lambda kv: abs(kv[0] - t))[1] if near else 950)
    res = list(out)
    for i, v in enumerate(out):
        if v is not None and not ((i > 0 and out[i - 1] is not None) or (i + 1 < len(out) and out[i + 1] is not None)):
            res[i] = None
    return res


def _exact_cut(cap, fps, t0, t1, to_split):
    """Thời điểm (chính xác tới từng khung) bố cục đổi: mặt người nói chuyển xuống / rời nửa dưới."""
    f0, f1 = max(0, int(round(t0 * fps)) - 3), int(round(t1 * fps)) + 3
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
    labels = []
    for _ in range(f0, f1 + 1):
        ok, fr = cap.read()
        if not ok:
            break
        labels.append(any(b[1] >= 1000 and b[2] >= 300 and 380 <= b[0] + b[2] / 2 <= 700 and b[4] >= 0.8 for b in F.detect(fr)))
    for k in range(len(labels)):
        if all(l == to_split for l in labels[k:]):
            return (f0 + k) / fps
    return (t0 + t1) / 2


def plan(video, segs, info, size=SIZE):
    times, faces, seams, fps = info["times"], info["faces"], info["seams"], info["fps"]
    states = _split_states(times, faces, seams)
    chunks = chunks_from_segments(segs)
    cap = cv2.VideoCapture(video)
    default_y = 1500
    ys, ys_top = list(range(700, 1840, 20)), list(range(260, 700, 20))
    layouts = [(540, 920), (320, 560), (760, 560)]
    res, cuts, prev = [], [], None
    for a, b, text in chunks:
        idx = [i for i, t in enumerate(times) if a - 0.05 <= t <= b + 0.05] or \
              [min(range(len(times)), key=lambda i: abs(times[i] - (a + b) / 2))]
        labels = ["S" if states[i] is not None else "N" for i in idx]
        for k in range(1, len(labels) - 1):
            if labels[k - 1] == labels[k + 1] != labels[k]:
                labels[k] = labels[k - 1]
        subs, s0 = [], a
        for k in range(1, len(idx)):
            if labels[k] != labels[k - 1]:
                cut = _exact_cut(cap, fps, times[idx[k - 1]], times[idx[k]], labels[k] == "S")
                cut = min(max(cut, a + 0.01), b - 0.01)
                subs.append((s0, cut, labels[k - 1]))
                cuts.append(round(cut, 4))
                s0 = cut
        subs.append((s0, b, labels[-1]))
        first = True
        for sa, sb, lab in subs:
            sidx = [i for i, t in enumerate(times) if sa - 0.12 <= t <= sb + 0.12 and (states[i] is not None) == (lab == "S")] or \
                   [i for i, t in enumerate(times) if sa - 0.12 <= t <= sb + 0.12]
            boxes = [x for i in sidx for x in faces[i]]
            seam = int(np.median([states[i] for i in sidx if states[i] is not None] or [954]))
            cbs = [seams[i][1] for i in sidx if seams[i]]
            cb = int(np.max(cbs)) if cbs else 0
            im1 = cap_img(text, 1000, size)
            roomy = (seam - cb) >= im1.shape[0] + 28
            if lab == "S" and roomy:                         # ngay dưới khung trên, trên đường chia
                h, w = im1.shape[:2]
                res.append(dict(a=sa, b=sb, text=text, cx=540, y=int(seam - 14 - h // 2), mw=1000, first=first, split=True))
                prev = None
            else:
                best = None
                for pool in (ys, ys_top):
                    for cx, mw in layouts:
                        im = cap_img(text, mw, size)
                        h, w = im.shape[:2]
                        for y in pool:
                            rect = (cx - w // 2, y - h // 2, cx + w // 2, y + h // 2)
                            if rect[0] < 24 or rect[2] > W - 24 or rect[1] < 120 or rect[3] > H - 90:
                                continue
                            ov = _overlap(rect, boxes)
                            cost = abs(y - default_y) / 100.0 + (0 if cx == 540 else 1.0) + (1.5 if (prev and (cx, y) != prev) else 0)
                            if ov > 0:
                                cost += 1000 + ov / 1000.0
                            if best is None or cost < best[0]:
                                best = (cost, cx, y, mw, ov == 0)
                    if best and best[4]:
                        break
                _, cx, y, mw, free = best
                prev = (cx, y)
                res.append(dict(a=sa, b=sb, text=text, cx=cx, y=y, mw=mw, first=first, split=False, free=free))
            first = False
    cap.release()
    for i in range(1, len(times)):                           # mọi chỗ đổi bố cục (cả giữa hai cụm chữ)
        if (states[i] is None) != (states[i - 1] is None):
            c = cv2.VideoCapture(video)
            cuts.append(round(_exact_cut(c, fps, times[i - 1], times[i], states[i] is not None), 4))
            c.release()
    return res, sorted(set(cuts))


# ----------------------------------------------------------------------------- in vào video
def burn(video, entries, cuts, out, audio_path=None, size=SIZE):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-",
           "-i", audio_path or video, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
           "-pix_fmt", "yuv420p", "-c:a", "copy" if not audio_path else "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        t = i / fps
        if not any(abs(t - c) <= 0.055 for c in cuts):         # ẩn ~0,1s ngay lúc đổi bố cục để không đè mặt
            for r in entries:
                if r["a"] <= t < r["b"]:
                    im = cap_img(r["text"], r["mw"], size)
                    h, w = im.shape[:2]
                    fade = min(1.0, (t - r["a"]) / 0.08) if r.get("first", True) else 1.0
                    E.blend(fr, im, r["cx"] - w // 2, r["y"] - h // 2, fade)
                    break
        p.stdin.write(fr.tobytes())
        if i % 300 == 0:
            print(f"  {t:6.1f}s", flush=True)
        i += 1
    p.stdin.close()
    p.wait()
    if p.returncode:
        raise SystemExit("ffmpeg lỗi khi in caption.")
    print("Xong:", out)


def audit(video, entries, cuts):
    """Kiểm tra lại trên VIDEO ĐÃ IN: có khung nào mặt chạm caption không. Trả về danh sách khung vi phạm."""
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    bad, n, i = [], 0, 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        t = i / fps
        r = None if any(abs(t - c) <= 0.055 for c in cuts) else next((p for p in entries if p["a"] <= t < p["b"]), None)
        if r and i % 2 == 0:
            im = cap_img(r["text"], r["mw"])
            h, w = im.shape[:2]
            rect = (r["cx"] - w // 2, r["y"] - h // 2, r["cx"] + w // 2, r["y"] + h // 2)
            n += 1
            for b in F.detect(fr):
                if b[2] >= 50 and b[4] >= 0.85 and _overlap(rect, [b], grow=0) > 0:
                    bad.append((round(t, 2), [int(v) for v in b[:4]]))
        i += 1
    return n, bad
