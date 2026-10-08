#!/usr/bin/env python3
"""Tạo bộ demo hoàn toàn tự sinh (không có video/ảnh của ai): người nói hoạt hình + tiếng đọc tổng hợp + ảnh minh họa giả.

    python make_demo.py            -> tạo source.mp4, assets/*.png, project.json trong thư mục này
    python ../../scripts/popedit.py render project.json

Tiếng đọc dùng TTS có sẵn của hệ điều hành (Windows SAPI / macOS say / Linux espeak-ng). Không có TTS thì tạo tiếng "bíp" thay thế.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SENTENCES = [
    "Hi everyone, today I will show you how to turn one plain video into a polished short.",
    "First, you just record yourself talking.",
    "In seven days this idea made two hundred and seventy six dollars.",
    "It works for health, for money, and for relationships.",
    "Meet Ann, Bob and Chloe.",
    "Then the assistant adds titles, cards and stickers.",
    "Finally, captions are placed so they never cover your face.",
    "That is it. Try it yourself.",
]
GAP = 0.35


# ----------------------------------------------------------------------------- tiếng đọc
def tts(text, out_wav):
    if sys.platform.startswith("win"):
        ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
              "try{$s.SelectVoice('Microsoft Zira Desktop')}catch{};$s.Rate=0;"
              f"$s.SetOutputToWaveFile('{out_wav}');$s.Speak('{text}');$s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    elif sys.platform == "darwin":
        subprocess.run(["say", "-o", out_wav + ".aiff", text], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out_wav + ".aiff", out_wav], check=True)
    elif shutil.which("espeak-ng"):
        subprocess.run(["espeak-ng", "-w", out_wav, text], check=True)
    else:
        n = int(48000 * (0.5 + 0.06 * len(text)))
        t = np.arange(n) / 48000
        y = 0.3 * np.sin(2 * np.pi * 220 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))
        with wave.open(out_wav, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
            w.writeframes((y * 32767).astype("<i2").tobytes())


def read_wav(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def build_audio():
    parts, starts, t = [], [], 0.0
    os.makedirs(os.path.join(HERE, "assets"), exist_ok=True)
    for i, s in enumerate(SENTENCES):
        p = os.path.join(HERE, f".s{i}.wav")
        tts(s, p)
        a = read_wav(p)
        os.remove(p)
        starts.append(t)
        parts += [a, np.zeros(int(GAP * 48000), np.float32)]
        t += len(a) / 48000 + GAP
    full = np.concatenate(parts)
    full = full / max(np.abs(full).max(), 1e-6) * 0.7
    wav = os.path.join(HERE, "voice.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes((full * 32767).astype("<i2").tobytes())
    return wav, full, starts + [t]


# ----------------------------------------------------------------------------- người nói hoạt hình
def draw_avatar(mouth, blink, bob):
    """Người nói hoạt hình có đổ bóng + hạt nhiễu nhẹ (để bộ nhận diện mặt bắt được như mặt thật)."""
    im = Image.new("RGB", (W, H), (226, 220, 210))
    d = ImageDraw.Draw(im)
    for y in range(H):
        c = int(226 - 22 * y / H)
        d.line([(0, y), (W, y)], fill=(c, c - 4, c - 14))
    cx, cy = 540, 700 + bob
    d.rounded_rectangle([140, 1060 + bob, 940, 2100], radius=260, fill=(60, 70, 110))              # áo
    d.rectangle([470, 930 + bob, 610, 1090 + bob], fill=(226, 176, 146))                             # cổ
    d.ellipse([cx - 235, cy - 330, cx + 235, cy + 330], fill=(48, 34, 30))                           # tóc sau
    d.rounded_rectangle([cx - 250, cy + 40, cx - 130, cy + 520], radius=60, fill=(48, 34, 30))
    d.rounded_rectangle([cx + 130, cy + 40, cx + 250, cy + 520], radius=60, fill=(48, 34, 30))
    d.ellipse([cx - 215, cy - 30, cx - 165, cy + 70], fill=(232, 184, 154))                          # tai
    d.ellipse([cx + 165, cy - 30, cx + 215, cy + 70], fill=(232, 184, 154))
    face = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(face).ellipse([cx - 190, cy - 240, cx + 190, cy + 250], fill=(240, 194, 164, 255))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.ellipse([cx - 190, cy - 240, cx + 190, cy + 250], outline=(150, 90, 70, 120), width=40)       # viền tối -> khối
    sd.ellipse([cx - 60, cy + 10, cx + 60, cy + 100], fill=(160, 100, 80, 60))
    sd.ellipse([cx - 150, cy + 60, cx - 60, cy + 150], fill=(235, 130, 130, 70))
    sd.ellipse([cx + 60, cy + 60, cx + 150, cy + 150], fill=(235, 130, 130, 70))
    face.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    im.paste(face, (0, 0), face)
    d = ImageDraw.Draw(im)
    d.pieslice([cx - 205, cy - 310, cx + 205, cy + 50], 180, 360, fill=(48, 34, 30))                 # tóc mái
    for ex in (-80, 80):
        if blink:
            d.line([(cx + ex - 40, cy - 5), (cx + ex + 40, cy - 5)], fill=(40, 30, 30), width=8)
        else:
            d.ellipse([cx + ex - 42, cy - 34, cx + ex + 42, cy + 30], fill=(250, 250, 250), outline=(90, 60, 50), width=5)
            d.ellipse([cx + ex - 20, cy - 26, cx + ex + 20, cy + 16], fill=(90, 60, 40))
            d.ellipse([cx + ex - 10, cy - 20, cx + ex + 10, cy + 8], fill=(20, 14, 12))
            d.ellipse([cx + ex - 5, cy - 18, cx + ex + 3, cy - 9], fill=(255, 255, 255))
            d.arc([cx + ex - 46, cy - 44, cx + ex + 46, cy + 20], 200, 340, fill=(30, 20, 18), width=7)
        d.arc([cx + ex - 52, cy - 86, cx + ex + 52, cy - 34], 205, 335, fill=(40, 28, 24), width=11)  # lông mày
    d.line([(cx - 8, cy - 20), (cx - 16, cy + 70)], fill=(200, 140, 115), width=6)                  # mũi
    d.polygon([(cx - 26, cy + 78), (cx, cy + 90), (cx + 26, cy + 78), (cx + 14, cy + 66), (cx - 14, cy + 66)], fill=(214, 152, 126))
    mh = int(6 + 64 * mouth)
    d.ellipse([cx - 58, cy + 128, cx + 58, cy + 128 + mh], fill=(120, 30, 44))                       # miệng
    d.pieslice([cx - 60, cy + 118, cx + 60, cy + 118 + mh + 16], 0, 180, fill=(200, 80, 92))
    d.polygon([(cx - 58, cy + 132), (cx, cy + 122), (cx + 58, cy + 132), (cx, cy + 142)], fill=(206, 92, 104))
    a = np.array(im).astype(np.float32)
    a += np.random.RandomState(3).randn(H, W, 1).astype(np.float32) * 4.0
    a = cv2.GaussianBlur(np.clip(a, 0, 255).astype(np.uint8), (0, 0), 1.2)
    return cv2.cvtColor(a, cv2.COLOR_RGB2BGR)


def build_video(voice_wav, full, total):
    out = os.path.join(HERE, "source.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", voice_wav, "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-shortest", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(total * FPS)
    hop = 48000 // FPS
    for i in range(n):
        seg = full[i * hop:(i + 1) * hop]
        amp = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
        mouth = min(1.0, amp * 5.0)
        blink = (i % 110) in (0, 1, 2, 3)
        bob = int(6 * math.sin(i / 14.0))
        p.stdin.write(draw_avatar(mouth, blink, bob).tobytes())
    p.stdin.close()
    p.wait()
    return out


# ----------------------------------------------------------------------------- ảnh minh họa giả
def _font(size, bold=True):
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_card_image(path, title, c1, c2, size=(1600, 900)):
    w, h = size
    im = Image.new("RGB", size, c1)
    d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] * (1 - k) + c2[i] * k) for i in range(3)))
    d.rounded_rectangle([80, 80, w - 80, 170], radius=30, fill=(255, 255, 255))
    d.ellipse([110, 105, 150, 145], fill=(255, 120, 120)); d.ellipse([165, 105, 205, 145], fill=(255, 200, 90)); d.ellipse([220, 105, 260, 145], fill=(120, 220, 140))
    for i in range(3):
        d.rounded_rectangle([80 + i * 500, 230, 80 + i * 500 + 450, 640], radius=30, fill=(255, 255, 255))
        d.rounded_rectangle([110 + i * 500, 270, 110 + i * 500 + 390, 400], radius=20, fill=(240, 240, 248))
        d.rounded_rectangle([110 + i * 500, 440, 110 + i * 500 + 280, 475], radius=12, fill=(220, 220, 232))
        d.rounded_rectangle([110 + i * 500, 505, 110 + i * 500 + 350, 530], radius=12, fill=(232, 232, 240))
    d.text((90, 700), title, font=_font(100), fill=(255, 255, 255))
    im.save(path)


def make_portrait(path, skin, hair, shirt, size=(760, 1000)):
    w, h = size
    im = Image.new("RGB", size, (236, 228, 240))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 640, w - 60, h + 300], radius=200, fill=shirt)
    d.rectangle([w // 2 - 50, 560, w // 2 + 50, 700], fill=skin)
    d.ellipse([w // 2 - 200, 130, w // 2 + 200, 600], fill=hair)
    d.ellipse([w // 2 - 160, 210, w // 2 + 160, 590], fill=skin)
    d.pieslice([w // 2 - 175, 150, w // 2 + 175, 400], 180, 360, fill=hair)
    for ex in (-70, 70):
        d.ellipse([w // 2 + ex - 28, 380, w // 2 + ex + 28, 430], fill=(255, 255, 255))
        d.ellipse([w // 2 + ex - 12, 390, w // 2 + ex + 12, 424], fill=(50, 36, 30))
    d.arc([w // 2 - 60, 450, w // 2 + 60, 540], 20, 160, fill=(150, 60, 70), width=8)
    im.save(path)


def make_logo(path):
    im = Image.new("RGBA", (1000, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 30, 190, 210], radius=40, fill=(236, 90, 130, 255))
    d.rounded_rectangle([60, 30, 190, 160], radius=40, fill=(255, 205, 70, 255))
    d.text((230, 55), "YourBrand", font=_font(130), fill=(20, 20, 30, 255))
    im.save(path)


def main():
    wav, full, starts = build_audio()
    print("tiếng đọc xong, tổng", round(starts[-1], 1), "giây")
    build_video(wav, full, starts[-1])
    os.remove(wav)
    A = os.path.join(HERE, "assets")
    os.makedirs(A, exist_ok=True)
    make_card_image(os.path.join(A, "screen1.png"), "Screen recording", (60, 120, 230), (120, 80, 220))
    make_card_image(os.path.join(A, "screen2.png"), "Dashboard", (240, 130, 90), (230, 70, 120))
    make_portrait(os.path.join(A, "ann.png"), (244, 200, 170), (50, 34, 30), (120, 90, 200))
    make_portrait(os.path.join(A, "bob.png"), (222, 170, 140), (90, 70, 50), (60, 150, 120))
    make_portrait(os.path.join(A, "chloe.png"), (250, 214, 190), (210, 150, 60), (230, 100, 120))
    make_logo(os.path.join(A, "logo.png"))
    s = starts
    d = lambda i, a=0.0: round(s[i] + a, 2)  # noqa: E731
    project = {
        "source": "source.mp4",
        "out": "out/demo.mp4",
        "theme": "be-hong",
        "audio": {"level": True, "sfx": True},
        "scenes": [
            {"t": [s[0], s[1]], "layout": "person"},
            {"t": [s[1], s[2]], "layout": "split", "bg": "light", "elements": [
                {"type": "title", "lines": [["lead", "step 1"], ["key", "Record yourself"]]},
                {"type": "media", "file": "assets/screen1.png", "show": [d(1, 0.3), s[2]], "tag": "Source: demo"}]},
            {"t": [s[2], s[3]], "layout": "full", "bg": "dark", "elements": [
                {"type": "title", "lines": [["lead", "revenue from one idea"]], "y": 560},
                {"type": "counter", "value": 276, "prefix": "$", "at": d(2, 1.2), "dur": 1.4, "y": 640},
                {"type": "title", "lines": [["lead", "in 7 days"]], "y": 1090, "show": [d(2, 2.4), s[3]]}]},
            {"t": [s[3], s[4]], "layout": "full", "bg": "light", "elements": [
                {"type": "title", "lines": [["lead", "works for"], ["key", "3 niches"]]},
                {"type": "card_list", "times": [d(3, 1.0), d(3, 1.6), d(3, 2.2)], "hide_at": s[4] - 0.3,
                 "items": [{"label": "Health", "icon": "health", "chips": ["herbs", "sleep", "food"]},
                           {"label": "Money", "icon": "money", "chips": ["invest", "save", "earn"]},
                           {"label": "Relationships", "icon": "love", "chips": ["dating", "family", "friends"]}]}]},
            {"t": [s[4], s[5]], "layout": "full", "bg": "light", "elements": [
                {"type": "slides", "header": "meet the characters", "items": [
                    {"file": "assets/ann.png", "name": "Ann", "sub": "28 · designer"},
                    {"file": "assets/bob.png", "name": "Bob", "sub": "45 · chef"},
                    {"file": "assets/chloe.png", "name": "Chloe", "sub": "22 · student"}]}]},
            {"t": [s[5], s[6]], "layout": "pip", "bg": "dark", "pip": {"pos": "bottom-right", "w": 400},
             "elements": [
                {"type": "title", "lines": [["lead", "then add"], ["key", "titles & stickers"]]},
                {"type": "media", "file": "assets/screen2.png", "show": [d(5, 0.2), s[6]], "box": [60, 520, 960, 760]},
                {"type": "sticker", "kind": "robot", "x": 200, "y": 1500, "size": 210, "at": d(5, 0.8)}]},
            {"t": [s[6], s[7]], "layout": "person"},
            {"t": [s[7], s[7] + 2.2], "layout": "full", "bg": "light", "elements": [
                {"type": "title", "lines": [["lead", "made with"]], "y": 520},
                {"type": "logo", "file": "assets/logo.png", "y": 900, "width": 900, "at": d(7, 0.3)}]},
            {"t": [s[7] + 2.2, s[8]], "layout": "person"},
        ],
    }
    json.dump(project, open(os.path.join(HERE, "project.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Xong: source.mp4, assets/, project.json")


if __name__ == "__main__":
    main()
