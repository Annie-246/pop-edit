#!/usr/bin/env python3
"""Dựng lại hình minh hoạ (khung chat, terminal, sơ đồ thư mục) và xuất HUONG-DAN.pdf từ guide.html.

    pip install playwright && python -m playwright install chromium
    python build_guide.py
"""
import html
import json
import os

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
FONT = os.path.join(os.path.expanduser("~"), ".popedit", "fonts")
URI = lambda p: "file:///" + p.replace("\\", "/")  # noqa: E731

CSS = f"""
@font-face {{ font-family:PJS; src:url('{URI(os.path.join(FONT,'PlusJakartaSans.ttf'))}'); font-weight:200 800; }}
@font-face {{ font-family:BRI; src:url('{URI(os.path.join(FONT,'BricolageGrotesque.ttf'))}'); font-weight:200 800; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:PJS,'Segoe UI',sans-serif; }}
.mono {{ font-family:Consolas,'Cascadia Mono','Courier New',monospace; }}
"""


def chat_html(title, turns, width=900):
    """turns: [("user"|"claude", html_text)]"""
    rows = ""
    for who, body in turns:
        if who == "user":
            rows += f'<div class="u"><div class="bub ub">{body}</div></div>'
        else:
            rows += f'<div class="c"><div class="av">✻</div><div class="bub cb">{body}</div></div>'
    return f"""<html><head><meta charset="utf-8"><style>{CSS}
    body{{background:#f4efe9;width:{width}px;padding:0}}
    .win{{background:#fbf8f4;border:1px solid #d9d0c5;border-radius:14px;overflow:hidden;box-shadow:0 8px 30px rgba(60,30,40,.12)}}
    .bar{{background:#ece4da;padding:10px 16px;font-size:14px;color:#5b4b4f;font-weight:600;display:flex;gap:8px;align-items:center}}
    .dot{{width:11px;height:11px;border-radius:50%;display:inline-block}}
    .body{{padding:22px 22px 8px}}
    .u{{display:flex;justify-content:flex-end;margin-bottom:16px}}
    .c{{display:flex;gap:12px;margin-bottom:16px}}
    .av{{width:30px;height:30px;border-radius:50%;background:#d97757;color:#fff;font-size:17px;display:flex;align-items:center;justify-content:center;flex:none}}
    .bub{{font-size:16px;line-height:1.55;padding:12px 16px;border-radius:14px;max-width:760px}}
    .ub{{background:#e9dfd4;color:#2b1f22}}
    .cb{{background:#fff;border:1px solid #eadfd6;color:#2b1f22}}
    table{{border-collapse:collapse;margin:8px 0;font-size:14px;width:100%}}
    td,th{{border:1px solid #e3d6ca;padding:5px 9px;text-align:left}} th{{background:#f5ece3}}
    code{{background:#f2ebe4;padding:1px 6px;border-radius:5px;font-family:Consolas,monospace;font-size:14px}}
    .tool{{font-family:Consolas,monospace;font-size:13.5px;background:#f6f1ec;border-left:3px solid #d97757;padding:7px 11px;margin:8px 0;color:#5b4b4f;white-space:pre-wrap}}
    ul{{margin:6px 0 6px 18px;padding:0}}
    </style></head><body><div class="win"><div class="bar"><span class="dot" style="background:#ff6b6b"></span><span class="dot" style="background:#ffc857"></span><span class="dot" style="background:#6bcB77"></span>&nbsp; {title}</div>
    <div class="body">{rows}</div></div></body></html>"""


def term_html(title, text, width=900, accent="#7ee787"):
    lines = ""
    for ln in text.split("\n"):
        e = html.escape(ln)
        if ln.startswith("PS ") or ln.startswith("$ ") or ln.startswith(">"):
            e = f'<span style="color:#79c0ff">{e}</span>'
        elif "THIẾU" in ln or "LỖI" in ln:
            e = f'<span style="color:#ffa657">{e}</span>'
        elif "✔" in ln or ln.startswith("Xong"):
            e = f'<span style="color:{accent}">{e}</span>'
        lines += e + "\n"
    return f"""<html><head><meta charset="utf-8"><style>{CSS}
    body{{background:#fff;width:{width}px}}
    .win{{background:#0d1117;border-radius:12px;overflow:hidden;box-shadow:0 8px 26px rgba(0,0,0,.25)}}
    .bar{{background:#1b222c;padding:9px 14px;font-size:13px;color:#9fb0c3;font-weight:600}}
    pre{{margin:0;padding:16px 18px;color:#d6dee8;font-family:Consolas,'Cascadia Mono',monospace;font-size:14.5px;line-height:1.5;white-space:pre-wrap}}
    </style></head><body><div class="win"><div class="bar">● ● ● &nbsp;{html.escape(title)}</div><pre>{lines}</pre></div></body></html>"""


def tree_html():
    return f"""<html><head><meta charset="utf-8"><style>{CSS}
    body{{background:#fff;width:900px}}
    .box{{background:#fbf8f4;border:1px solid #e3d6ca;border-radius:12px;padding:20px 26px;font-family:Consolas,monospace;font-size:16px;line-height:1.7;color:#2b1f22}}
    .n{{color:#9a8a8e;font-family:PJS,sans-serif;font-size:14px;margin-left:10px}} b{{color:#b83e62}}
    </style></head><body><div class="box">
<b>video-cua-toi/</b><br>
├─ <b>source.mp4</b> <span class="n">← video quay mặt, dọc 9:16, 1080×1920 (bắt buộc)</span><br>
├─ assets/ <span class="n">← ảnh/clip minh họa (đặt tên dễ nhớ)</span><br>
│&nbsp;&nbsp;├─ man-hinh-1.png<br>
│&nbsp;&nbsp;├─ nhan-vat-a.png<br>
│&nbsp;&nbsp;├─ clip-demo.mp4<br>
│&nbsp;&nbsp;└─ logo.png <span class="n">← logo nền trong (tuỳ chọn)</span><br>
├─ nhac.mp3 <span class="n">← nhạc nền được phép dùng (tuỳ chọn)</span><br>
└─ ghi-chu.txt <span class="n">← kịch bản / ý muốn nói với Claude (tuỳ chọn)</span><br>
<br>
<span class="n" style="margin:0">Claude sẽ tự tạo thêm:</span><br>
├─ project.json <span class="n">← "bảng dựng": cảnh nào, kiểu gì, hình gì</span><br>
├─ captions.json <span class="n">← phụ đề đã sửa lỗi</span><br>
└─ out/final.mp4 <span class="n">← video thành phẩm</span>
    </div></body></html>"""


def _launch(pw):
    """Thử Chromium của Playwright; nếu chưa cài thì dùng Edge/Chrome có sẵn trên máy."""
    for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
        try:
            return pw.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    raise SystemExit("Không mở được trình duyệt. Chạy: python -m playwright install chromium")


def shot(page, html_text, out_png, selector="body"):
    page.set_content(html_text, wait_until="load")
    page.wait_for_timeout(300)
    page.locator(selector).screenshot(path=out_png)


def main():
    os.makedirs(IMG, exist_ok=True)
    plan_rows = [("0 – 2", "person", "Chào, mở đầu"),
                 ("2 – 6", "split", "Tiêu đề “Record yourself” + ảnh màn hình"),
                 ("6 – 11", "full", "Số $276 đếm lên"),
                 ("11 – 17", "full", "3 thẻ pop-up: Health / Money / Relationships"),
                 ("17 – 24", "full", "Nhân vật full khung, swipe từng người"),
                 ("24 – 31", "pip", "Ảnh Dashboard + sticker robot, người nói thu nhỏ góc"),
                 ("31 – 35", "person → full", "Kết + logo")]
    plan_tbl = "<table><tr><th>Giây</th><th>Kiểu</th><th>Hình / chữ</th></tr>" + "".join(
        f"<tr><td>{a}</td><td><code>{b}</code></td><td>{c}</td></tr>" for a, b, c in plan_rows) + "</table>"

    chat1 = chat_html("Claude Code — thư mục video-cua-toi", [
        ("user", "Dựng giúp mình video này theo kiểu <code>pop-edit</code>. Source là <code>source.mp4</code>, ảnh minh họa trong <code>assets/</code>. "
                 "<b>Chưa dựng vội</b>, đưa mình bảng kế hoạch giây → kiểu → hình gì để mình duyệt."),
        ("claude", "Mình đã kiểm tra: source 1080×1920, 30 fps, dài 35 giây. Đã bóc băng lời nói và sửa tên riêng.<div class='tool'>$ python popedit.py transcribe source.mp4 --lang en\n→ 8 câu</div>"
                   "Đây là kế hoạch đề xuất:" + plan_tbl + "Bạn duyệt giúp mình, hoặc chỉnh chỗ nào thì nói nhé."),
        ("user", "Ổn rồi. Đổi đoạn 6–11 sang nền đậm cho nổi số nhé."),
    ])
    chat2 = chat_html("Claude Code — xem thử trước khi render", [
        ("claude", "Đã sửa nền. Mình xuất bảng ảnh thu nhỏ để kiểm tra trước khi render đủ:<div class='tool'>$ python popedit.py sheet project.json --every 2.5\n→ .popedit/sheet.png</div>"
                   "Mình đã mở ảnh xem:<ul><li>Chữ không tràn khung ✔</li><li>Thẻ pop-up không che mặt ✔</li><li>Đoạn 24–31s: sticker hơi gần ảnh, mình dời xuống 40px</li></ul>Mình render bản đầy đủ nhé?"),
        ("user", "Ok render đi."),
        ("claude", "Xong: <code>out/final.mp4</code> (35,2 giây, 1080×1920). <b>Chưa kiểm được:</b> mình chưa nghe bằng tai, bạn nghe thử giúp mình phần tiếng nhé."),
    ])
    chat3 = chat_html("Claude Code — thêm caption né mặt", [
        ("user", "Chèn phụ đề vào video, đảm bảo caption không che mặt. Che cổ được."),
        ("claude", "Mình bóc băng, sửa lỗi nghe nhầm rồi đặt caption:<div class='tool'>$ python popedit.py captions out/final.mp4 --segments captions.json --level --audit\n"
                   "     14 đoạn chữ, 5 đoạn được dời khỏi vị trí mặc định để né mặt\n     384 khung có caption, mặt chạm caption: 0</div>"
                   "Ở cảnh chia đôi, chữ nằm ngay dưới khung trên. Tiếng cũng đã được làm đều. <b>Lưu ý:</b> chữ có thể che cổ/tay (bạn cho phép), và nhận diện mặt có thể nhầm bàn tay."),
    ])
    term_install_win = ("PS C:\\Users\\ban> irm https://claude.ai/install.ps1 | iex\n"
                        "PS C:\\Users\\ban> claude --version\n2.1.269 (Claude Code)\n"
                        "PS C:\\Users\\ban> cd C:\\video-cua-toi\nPS C:\\video-cua-toi> claude")
    term_setup = ("$ python popedit.py setup\npopedit 1.0.0\n"
                  "Tải font + model nhận diện mặt vào C:\\Users\\ban\\.popedit\n"
                  "  tải BricolageGrotesque.ttf ...\n  tải PlusJakartaSans.ttf ...\n  tải PlusJakartaSans-Italic.ttf ...\n"
                  "  tải face_detection_yunet_2023mar.onnx ...\n\nSẴN SÀNG ✔")
    term_render = ("$ python popedit.py render project.json\n    0.0s / 35.2s\n    5.0s / 35.2s\n   10.0s / 35.2s\n   ...\n   35.0s / 35.2s\n"
                   "Xong: C:\\video-cua-toi\\out\\demo.mp4")
    term_miss = ("$ python popedit.py setup\n  THIẾU  faster_whisper   ->  pip install faster-whisper\n"
                 "  THIẾU  ffmpeg  ->  Windows: winget install Gyan.FFmpeg   |   macOS: brew install ffmpeg\n\n"
                 "Còn thiếu thứ cần cài (xem các dòng THIẾU ở trên).")
    term_skill = ("> /plugin marketplace add Annie-246/pop-edit\n> /plugin install pop-edit@pop-edit")

    with sync_playwright() as pw:
        b = _launch(pw)
        pg = b.new_page(viewport={"width": 960, "height": 800}, device_scale_factor=2)
        shot(pg, chat1, os.path.join(IMG, "chat1.png"), ".win")
        shot(pg, chat2, os.path.join(IMG, "chat2.png"), ".win")
        shot(pg, chat3, os.path.join(IMG, "chat3.png"), ".win")
        shot(pg, term_html("PowerShell", term_install_win), os.path.join(IMG, "term_install.png"), ".win")
        shot(pg, term_html("Terminal", term_setup), os.path.join(IMG, "term_setup.png"), ".win")
        shot(pg, term_html("Terminal", term_render), os.path.join(IMG, "term_render.png"), ".win")
        shot(pg, term_html("Terminal — khi còn thiếu", term_miss), os.path.join(IMG, "term_missing.png"), ".win")
        shot(pg, term_html("Claude Code", term_skill), os.path.join(IMG, "term_plugin.png"), ".win")
        shot(pg, tree_html(), os.path.join(IMG, "tree.png"), ".box")
        # ---- PDF
        pg2 = b.new_page()
        src = open(os.path.join(HERE, "guide.html"), encoding="utf-8").read().replace("{{FONT}}", URI(FONT))
        tmp = os.path.join(HERE, "_guide.rendered.html")
        open(tmp, "w", encoding="utf-8").write(src)
        pg2.goto(URI(tmp), wait_until="load")
        pg2.wait_for_timeout(800)
        pg2.pdf(path=os.path.join(HERE, "HUONG-DAN.pdf"), format="A4", print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"},
                display_header_footer=True,
                header_template="<span></span>",
                footer_template="<div style='font-size:9px;width:100%;text-align:center;color:#9a8a8e'>pop-edit — hướng dẫn · trang <span class='pageNumber'></span>/<span class='totalPages'></span></div>")
        b.close()
    os.remove(tmp)
    print("Đã tạo:", os.path.join(HERE, "HUONG-DAN.pdf"))


if __name__ == "__main__":
    main()
