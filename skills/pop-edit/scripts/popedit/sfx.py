"""Sound effect tự tổng hợp bằng numpy (không cần tải file, không dính bản quyền): whoosh, swipe, pop, impact."""
import wave

import numpy as np

SR = 48000


def _env(n, attack=0.01, decay=1.0, curve=2.0):
    a = max(1, int(n * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[a:] = np.linspace(1, 0, n - a) ** curve
    return e * decay


def _noise(n, seed=7):
    return np.random.RandomState(seed).randn(n)


def _lowpass(x, cutoff):
    rc = 1.0 / (2 * np.pi * max(20.0, cutoff))
    a = (1.0 / SR) / (rc + 1.0 / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def whoosh(dur=0.55):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = _noise(n)
    cut = 400 + 4600 * np.sin(np.pi * t)                 # quét tần số 400 -> 5000 -> 600 Hz
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        rc = 1.0 / (2 * np.pi * cut[i])
        a = (1.0 / SR) / (rc + 1.0 / SR)
        acc += a * (x[i] - acc)
        y[i] = acc
    y *= _env(n, 0.15, 1.0, 1.6)
    return np.stack([y, np.roll(y, 240)], axis=1)


def swipe(dur=0.28):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    y = _lowpass(_noise(n, 11), 6000) * (np.sin(np.pi * t) ** 1.4) * 0.8
    return np.stack([y * 0.7, y], axis=1)


def pop(dur=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-14 * t)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 1.0, 4.0)
    return np.stack([y, y], axis=1)


def impact(dur=0.7):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 90 * np.exp(-3.0 * t)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 1.0, 2.6)
    click = _lowpass(_noise(n, 5), 2200) * _env(n, 0.001, 0.6, 5.0)
    y = body * 0.9 + click
    return np.stack([y, y], axis=1)


BANK = dict(whoosh=whoosh, swipe=swipe, pop=pop, impact=impact)


def render_track(events, total_dur, peak_db=-24.0):
    """events: [(giây, tên, gain_dB)]. Đặt SFX sớm hơn hình ~0,08s. Chuẩn hoá đỉnh về peak_db."""
    n = int(total_dur * SR) + SR
    buf = np.zeros((n, 2))
    cache = {}
    for t, name, gdb in events:
        if name not in BANK:
            continue
        if name not in cache:
            cache[name] = BANK[name]()
        s = cache[name] * 10 ** (gdb / 20.0)
        i0 = max(0, int((t - 0.08) * SR))
        i1 = min(n, i0 + len(s))
        buf[i0:i1] += s[:i1 - i0]
    peak = np.abs(buf).max()
    if peak > 0:
        buf *= 10 ** (peak_db / 20.0) / peak
    return buf


def write_wav(path, buf):
    data = (np.clip(buf, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path
