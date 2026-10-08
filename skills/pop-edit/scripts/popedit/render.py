"""Dựng video từ project.json: hình (OpenCV) -> ffmpeg (x264) + trộn tiếng nói + SFX + nhạc nền."""
import os
import subprocess
import sys

import cv2
import numpy as np

from . import audio, engine as E, sfx
from .timeline import Project

W, H = E.W, E.H


def _sfx_events(scenes):
    ev = []
    for i, sc in enumerate(scenes):
        if i > 0 and not (sc.is_person and scenes[i - 1].is_person):
            ev.append((sc.t0 - 0.14, "whoosh", -15))
        for el in sc.elems:
            if isinstance(el, E.Media) and el.start > 0.3:
                ev.append((sc.t0 + el.start, "pop", -17))
            elif isinstance(el, E.Cards):
                ev += [(sc.t0 + el.start + k * el.stagger, "pop", -17) for k in range(len(el.cards))]
            elif isinstance(el, E.CardList):
                ev += [(sc.t0 + s, "pop", -15) for s in el.starts]
            elif isinstance(el, E.Sticker):
                ev.append((sc.t0 + el.start, "pop", -15))
            elif isinstance(el, E.Counter):
                ev.append((sc.t0 + el.start + el.dur, "impact", -15))
            elif isinstance(el, E.Slides):
                ev += [(sc.t0 + k * el.slot, "swipe", -13) for k in range(1, len(el.items))]
    return ev


def _scene_at(scenes, t):
    for s in scenes:
        if s.t0 <= t < s.t1:
            return s
    return scenes[-1]


class Renderer:
    def __init__(self, project_path):
        self.p = Project(project_path)
        self.cache = os.path.join(self.p.dir, ".popedit")
        os.makedirs(self.cache, exist_ok=True)
        self.music_plan = None
        boundaries = None
        mus = self.p.audio.get("music")
        if mus and mus.get("beat_snap"):
            raws = self.p.raw_scenes()
            self.music_plan = audio.beat_plan(self.p.abs(mus["file"]), [r["t"][0] for r in raws[1:]])
            Tv, o = self.music_plan["Tv"], self.music_plan["o"]
            boundaries = {}
            for i in range(1, len(raws)):
                t = raws[i]["t"][0]
                nb = o + round((t - o) / Tv) * Tv
                if abs(nb - t) <= 0.22:
                    boundaries[i] = nb
            self._shift_shows(raws, boundaries)
        self.scenes = self.p.build(boundaries)
        self.bounds = [s.t0 for s in self.scenes[1:]]
        self.cap = cv2.VideoCapture(self.p.source)
        self.state = {"pos": -1, "last": None}
        self.canvas = np.zeros((H, W, 3), np.uint8)

    @staticmethod
    def _shift_shows(raws, boundaries):
        """Khi nhích mốc cảnh về nhịp, kéo đầu/cuối của 'show' đang trùng mốc cũ theo mốc mới."""
        for i, nb in boundaries.items():
            old = raws[i]["t"][0]
            for j in (i - 1, i):
                for e in raws[j].get("elements", []):
                    if "show" in e:
                        for k in (0, 1):
                            if abs(e["show"][k] - old) < 0.15:
                                e["show"][k] = nb

    # ---- khung người nói
    def person_frame(self, t):
        want = int(round(t * self.p.fps))
        st = self.state
        if want < st["pos"] or want - st["pos"] > 60:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, want)
            st["pos"] = want - 1
        while st["pos"] < want:
            ok, fr = self.cap.read()
            if not ok:
                break
            st["pos"] += 1
            st["last"] = fr
        return st["last"] if st["last"] is not None else np.zeros((H, W, 3), np.uint8)

    def frame(self, t):
        sc = _scene_at(self.scenes, t)
        near = any(abs(t - b) < 0.23 for b in self.bounds)
        need = sc.layout in ("person", "split", "pip") or near
        pf = self.person_frame(t) if need else np.zeros((H, W, 3), np.uint8)
        sc.render(self.canvas, t, pf)
        for b in self.bounds:
            if abs(t - b) < 0.22:
                E.wipe(self.canvas, t, b)
        return self.canvas

    # ---- âm thanh
    def mix_inputs(self, a, b):
        au = self.p.audio
        dur = self.p.duration
        inputs, labels = [], []
        voice = self.p.source
        if au.get("level", True):
            voice = os.path.join(self.cache, "voice_leveled.wav")
            if not os.path.exists(voice):
                print("Làm đều tiếng nói ...", flush=True)
                audio.level_voice(self.p.source, voice)
        inputs.append(voice)
        weights = []
        if au.get("sfx", True):
            path = os.path.join(self.cache, "sfx.wav")
            sfx.write_wav(path, sfx.render_track(_sfx_events(self.scenes), dur, peak_db=au.get("sfx_peak_db", -14)))
            inputs.append(path)
        mus = au.get("music")
        if mus:
            vwav = os.path.join(self.cache, "voice_for_duck.wav")
            if not os.path.exists(vwav):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.p.source, "-vn", "-ac", "2", "-ar", "48000", vwav], check=True)
            bed = os.path.join(self.cache, "music_bed.wav")
            plan = self.music_plan or {"r": 1.0, "delay": 0.0}
            audio.music_bed(self.p.abs(mus["file"]), vwav, bed, dur, gain_db=mus.get("gain_db", -2.0), rate=plan["r"], delay=plan["delay"])
            inputs.append(bed)
        return inputs

    # ---- chạy
    def render(self, a=None, b=None, out=None):
        a0 = 0.0 if a is None else a
        b0 = self.p.duration if b is None else b
        out = out or (self.p.out if a is None else os.path.join(self.cache, "preview.mp4"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        inputs = self.mix_inputs(a0, b0)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", f"{self.p.fps}", "-i", "-"]
        for f in inputs:
            cmd += ["-ss", f"{a0}", "-t", f"{b0 - a0}", "-i", f]
        if len(inputs) > 1:
            ins = "".join(f"[{i + 1}:a]" for i in range(len(inputs)))
            fc = f"{ins}amix=inputs={len(inputs)}:duration=first:normalize=0,alimiter=limit=0.97[aout]"
            cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "-shortest", out]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = int(round((b0 - a0) * self.p.fps))
        for i in range(n):
            t = a0 + i / self.p.fps
            proc.stdin.write(self.frame(t).tobytes())
            if i % 150 == 0:
                print(f"  {t:6.1f}s / {b0:.1f}s", flush=True)
        proc.stdin.close()
        proc.wait()
        if proc.returncode:
            raise SystemExit("ffmpeg lỗi — xem thông báo phía trên.")
        print("Xong:", out)
        return out

    def stills(self, times, outdir=None):
        outdir = outdir or os.path.join(self.cache, "stills")
        os.makedirs(outdir, exist_ok=True)
        paths = []
        for t in times:
            fr = self.frame(float(t))
            p = os.path.join(outdir, f"t_{float(t):07.2f}.png")
            cv2.imencode(".png", fr)[1].tofile(p)
            paths.append(p)
        return paths

    def contact_sheet(self, times, out_png, cols=6, w=270):
        tiles = []
        for t in times:
            fr = cv2.resize(self.frame(float(t)), (w, int(w * H / W))).copy()
            cv2.putText(fr, f"{float(t):.1f}s", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            tiles.append(fr)
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        cv2.imencode(".png", np.vstack(rows))[1].tofile(out_png)
        return out_png
