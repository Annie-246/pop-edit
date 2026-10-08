"""Âm thanh: làm đều tiếng nói, dựng nền nhạc (lặp + hạ khi có lời + khớp nhịp), đo độ đều."""
import os
import subprocess

import numpy as np

SR = 48000


def _run(cmd):
    subprocess.run(cmd, check=True)


def decode(path, ch=2, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    return x.reshape(-1, ch).copy() if ch > 1 else x.copy()


def loudness_profile(path):
    """RMS từng giây (dBFS) của đoạn có tiếng nói + thống kê."""
    x = decode(path, 1, 16000)
    sr = 16000
    n = len(x) // sr
    rms = np.array([20 * np.log10(np.sqrt(np.mean(x[i * sr:(i + 1) * sr] ** 2)) + 1e-9) for i in range(n)])
    peak = float(20 * np.log10(np.abs(x).max() + 1e-9))
    sp = rms[rms > -35]
    return dict(mean=float(sp.mean()), std=float(sp.std()), min=float(sp.min()), max=float(sp.max()), peak=peak, per_sec=rms)


def level_voice(src, out_wav, target_db=-13.0, max_cut=-9.0, max_boost=11.0, loudnorm_i=-15.0):
    """Kéo phần nói về cùng 1 mức: đường cong gain mượt theo mức nói cục bộ -> nén nhẹ -> chuẩn hoá -> chặn đỉnh."""
    x = decode(src, 2)
    mono = x.mean(1)
    hop, win = int(0.1 * SR), int(0.4 * SR)
    n = len(mono) // hop
    env = np.array([np.sqrt(np.mean(mono[max(0, i * hop - win // 2): i * hop + win // 2] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(env + 1e-9)
    speech = db > -38
    lvl = np.full(n, np.nan)
    for i in range(n):
        lo, hi = max(0, i - 25), i + 26
        seg = db[lo:hi][speech[lo:hi]]
        if len(seg) >= 5:
            lvl[i] = np.percentile(seg, 70)
    idx = np.arange(n)
    ok = ~np.isnan(lvl)
    if ok.sum() == 0:
        raise SystemExit("Không thấy tiếng nói trong file nguồn.")
    lvl = np.interp(idx, idx[ok], lvl[ok])
    gain_db = np.clip(target_db - lvl, max_cut, max_boost)
    k = np.ones(12) / 12
    gain_db = np.convolve(np.pad(gain_db, 6, mode="edge"), k, mode="same")[6:-6]
    g = 10 ** (np.interp(np.arange(len(mono)) / SR, idx * hop / SR, gain_db) / 20.0)
    y = (x * g[:, None]).astype(np.float32)
    pre = out_wav + ".pre.f32"
    open(pre, "wb").write(y.tobytes())
    _run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", pre, "-af",
          f"acompressor=threshold=0.18:ratio=3.2:attack=8:release=140:makeup=1.6,loudnorm=I={loudnorm_i}:LRA=5:TP=-1.5,alimiter=limit=0.9",
          "-ar", str(SR), out_wav])
    os.remove(pre)
    return out_wav


def music_bed(music_file, voice_wav, out_wav, dur, gain_db=-9.0, rate=1.0, delay=0.0, fade_out=3.0):
    """Lặp nhạc cho đủ dài (crossfade 3s), đổi tốc độ nhẹ, hạ khi có lời (sidechain)."""
    d = int(delay * 1000)
    raw = out_wav + ".raw.wav"
    _run(["ffmpeg", "-v", "error", "-y", "-i", music_file, "-i", music_file, "-filter_complex",
          "[0:a][1:a]acrossfade=d=3:c1=tri:c2=tri,aresample=48000,aformat=channel_layouts=stereo,"
          f"atempo={rate:.4f},adelay={d}|{d},atrim=0:{dur + 0.3:.2f},afade=t=in:st=0:d=1.2,afade=t=out:st={max(dur - fade_out, 0):.2f}:d={fade_out}[a]",
          "-map", "[a]", raw])
    _run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", voice_wav, "-filter_complex",
          f"[0:a][1:a]sidechaincompress=threshold=0.04:ratio=3:attack=20:release=500,volume={gain_db}dB[m]",
          "-map", "[m]", out_wav])
    os.remove(raw)
    return out_wav


def beat_plan(music_file, boundaries, rate_range=(0.94, 1.08)):
    """Chọn tốc độ nhạc r và độ lệch o sao cho các mốc chuyển cảnh rơi gần nhịp nhất. Cần librosa (tuỳ chọn)."""
    try:
        import librosa
    except ImportError:
        raise SystemExit("beat_snap cần: pip install librosa")
    y, sr = librosa.load(music_file, sr=22050)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", start_bpm=105)
    T0 = float(np.median(np.diff(beats)))
    if T0 > 0.75:           # bộ dò hay khóa nửa nhịp
        T0 /= 2
    b0 = float(beats[0] - T0 * round(beats[0] / T0))
    B = np.array(boundaries)
    best = None
    for r in np.arange(rate_range[0], rate_range[1] + 1e-6, 0.0025):
        Tv = T0 / r
        for o in np.arange(0, Tv, 0.01):
            d = np.abs(((B - o) / Tv + 0.5) % 1 - 0.5) * Tv
            m = float(np.mean(d))
            if best is None or m < best[0]:
                best = (m, float(r), float(o))
    _, r, o = best
    return dict(T=T0, b0=b0, r=r, o=o, Tv=T0 / r, delay=(o - b0 / r) % (T0 / r))
