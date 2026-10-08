"""Dòng lệnh:  python popedit.py <lệnh> ...   (chạy `python popedit.py -h` để xem tất cả)"""
import argparse
import importlib
import json
import os
import shutil
import sys

from . import __version__, assets


def _need(mod, pip):
    try:
        importlib.import_module(mod)
        return True
    except ImportError:
        print(f"  THIẾU  {mod}   ->  pip install {pip}")
        return False


def cmd_setup(a):
    print(f"popedit {__version__}")
    ok = True
    for m, pipname in (("cv2", "opencv-python"), ("numpy", "numpy"), ("PIL", "pillow"), ("faster_whisper", "faster-whisper")):
        ok &= _need(m, pipname)
    if shutil.which("ffmpeg") is None:
        print("  THIẾU  ffmpeg  ->  Windows: winget install Gyan.FFmpeg   |   macOS: brew install ffmpeg")
        ok = False
    print("Tải font + model nhận diện mặt vào", assets.HOME)
    ok &= assets.ensure()
    print("\nSẴN SÀNG ✔" if ok else "\nCòn thiếu thứ cần cài (xem các dòng THIẾU ở trên).")
    return 0 if ok else 1


def cmd_new(a):
    os.makedirs(a.dir, exist_ok=True)
    proj = {
        "source": a.source,
        "out": "out/final.mp4",
        "theme": "be-hong",
        "audio": {"level": True, "sfx": True},
        "scenes": [
            {"t": [0, 2.0], "layout": "person"},
            {"t": [2.0, 6.0], "layout": "split", "bg": "light", "elements": [
                {"type": "title", "lines": [["lead", "chữ dẫn nhỏ"], ["key", "Tiêu đề chính"]]},
                {"type": "media", "file": "assets/anh1.png", "show": [2.2, 6.0], "tag": "Nguồn: ..."}]},
        ],
    }
    p = os.path.join(a.dir, "project.json")
    if os.path.exists(p):
        raise SystemExit(f"{p} đã có.")
    json.dump(proj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(a.dir, "assets"), exist_ok=True)
    print("Đã tạo", p)


def cmd_stills(a):
    from .render import Renderer
    r = Renderer(a.project)
    paths = r.stills(a.times, a.outdir)
    for p in paths:
        print(p)


def cmd_sheet(a):
    from .render import Renderer
    r = Renderer(a.project)
    times = [round(i * a.every, 2) for i in range(int(r.p.duration / a.every) + 1)]
    out = a.out or os.path.join(r.cache, "sheet.png")
    r.contact_sheet(times, out, cols=a.cols)
    print(out)


def cmd_render(a):
    from .render import Renderer
    r = Renderer(a.project)
    r.render(a.start, a.end, a.out)


def cmd_transcribe(a):
    from . import captions
    out = a.out or os.path.splitext(a.video)[0] + ".captions.draft.json"
    segs = captions.transcribe(a.video, out, lang=a.lang, model=a.model, prompt=a.prompt)
    print(f"{len(segs)} câu -> {out}")
    for i, s in enumerate(segs):
        print(f"{i:3d} {s['start']:7.2f}-{s['end']:7.2f}  {s['text']}")


def cmd_captions(a):
    from . import audio, captions, faces
    segs = json.load(open(a.segments, encoding="utf-8"))
    out = a.out or os.path.splitext(a.video)[0] + " - caption.mp4"
    work = os.path.join(os.path.dirname(os.path.abspath(a.video)), ".popedit")
    os.makedirs(work, exist_ok=True)
    print("1/3  Quét mặt + bố cục ...")
    info = faces.analyze(a.video, cache=os.path.join(work, "faces_" + os.path.basename(a.video) + ".json"))
    print("2/3  Đặt vị trí caption ...")
    entries, cuts = captions.plan(a.video, segs, info, size=a.size)
    json.dump(dict(entries=entries, cuts=cuts), open(os.path.join(work, "caption_plan.json"), "w", encoding="utf-8"), ensure_ascii=False)
    moved = sum(1 for e in entries if (e["cx"], e["y"]) != (540, 1500))
    print(f"     {len(entries)} đoạn chữ, {moved} đoạn được dời khỏi vị trí mặc định để né mặt")
    audio_path = None
    if a.level:
        audio_path = os.path.join(work, "voice_leveled.wav")
        print("     Làm đều tiếng ...")
        audio.level_voice(a.video, audio_path)
    print("3/3  In caption vào video ...")
    captions.burn(a.video, entries, cuts, out, audio_path, size=a.size)
    if a.audit:
        print("Kiểm tra lại video đã in ...")
        n, bad = captions.audit(out, entries, cuts)
        print(f"     {n} khung có caption, mặt chạm caption: {len(bad)}  {bad[:6]}")


def cmd_level(a):
    from . import audio
    before = audio.loudness_profile(a.video)
    out = a.out or os.path.splitext(a.video)[0] + ".leveled.wav"
    audio.level_voice(a.video, out)
    after = audio.loudness_profile(out)
    print(f"Trước: trung bình {before['mean']:.1f} dB, lệch giữa các đoạn {before['std']:.2f} dB, đỉnh {before['peak']:+.1f} dBFS")
    print(f"Sau:   trung bình {after['mean']:.1f} dB, lệch giữa các đoạn {after['std']:.2f} dB, đỉnh {after['peak']:+.1f} dBFS")
    print("->", out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="popedit", description="Dựng video talking-head dọc 9:16 kiểu typo-pop.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="kiểm tra máy + tải font/model").set_defaults(fn=cmd_setup)

    p = sub.add_parser("new", help="tạo project.json mẫu")
    p.add_argument("dir")
    p.add_argument("--source", default="source.mp4")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("stills", help="xuất vài khung hình để xem thử")
    p.add_argument("project")
    p.add_argument("times", nargs="+", type=float)
    p.add_argument("--outdir")
    p.set_defaults(fn=cmd_stills)

    p = sub.add_parser("sheet", help="bảng ảnh thu nhỏ cả video để duyệt nhanh")
    p.add_argument("project")
    p.add_argument("--every", type=float, default=2.5)
    p.add_argument("--cols", type=int, default=8)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_sheet)

    p = sub.add_parser("render", help="dựng video")
    p.add_argument("project")
    p.add_argument("--from", dest="start", type=float)
    p.add_argument("--to", dest="end", type=float)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("transcribe", help="bóc băng -> captions.draft.json")
    p.add_argument("video")
    p.add_argument("--lang", default="vi")
    p.add_argument("--model", default="medium", help="tiny/base/small/medium/large-v3 (medium chính xác hơn, chậm hơn)")
    p.add_argument("--prompt", help="gợi ý tên riêng/thuật ngữ cho Whisper, vd: 'TenRieng, Instagram'")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_transcribe)

    p = sub.add_parser("captions", help="in caption né mặt vào video")
    p.add_argument("video")
    p.add_argument("--segments", required=True, help="captions.json (đã sửa chữ)")
    p.add_argument("--out")
    p.add_argument("--size", type=int, default=58)
    p.add_argument("--level", action="store_true", help="đồng thời làm đều tiếng")
    p.add_argument("--audit", action="store_true", help="kiểm tra lại video đã in")
    p.set_defaults(fn=cmd_captions)

    p = sub.add_parser("level", help="làm đều tiếng nói, in số liệu trước/sau")
    p.add_argument("video")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_level)

    a = ap.parse_args(argv)
    sys.exit(a.fn(a) or 0)
