---
name: pop-edit
description: Dựng video talking-head dọc 9:16 kiểu "typo-pop" từ 1 video người nói + ảnh/clip minh họa, bằng code (Python + OpenCV + ffmpeg). Gồm chữ tiêu đề đậm có ô chọn chữ, bố cục chia đôi (minh họa trên - người nói dưới), thẻ minh họa bật lên, danh sách pop-up theo lời nói, số đếm lên, sticker, màn nhân vật full khung có swipe, người nói thu nhỏ góc (PiP), logo, chuyển cảnh quét màu, SFX tự tổng hợp, nhạc nền hạ khi có lời, làm đều tiếng nói, và caption tự đặt né mặt. Dùng khi người dùng nói "edit video", "dựng video", "thêm caption", "làm đều tiếng", "chia đôi màn hình", "pop-edit", hoặc đưa video quay mặt kèm ảnh minh họa muốn làm thành short/reel/TikTok.
---

# pop-edit — dựng video typo-pop 9:16

Bạn là người dựng. Người dùng đưa **1 video người nói** (1080x1920) + **ảnh/clip minh họa**; bạn viết file `project.json`
rồi chạy `popedit.py` để ra video. **Không có phần mềm dựng nào, mọi thứ là code** nên sửa 1 chỗ là render lại được.

Đường dẫn trong tài liệu này viết tắt `PE` = `<thư mục skill>/scripts/popedit.py`
(cài qua marketplace thì `~/.claude/plugins/.../skills/pop-edit/scripts/popedit.py`; cài tay thì `~/.claude/skills/pop-edit/scripts/popedit.py`).
Hãy tìm đúng đường dẫn bằng `find`/`Glob` tên `popedit.py` trước khi chạy.

## 0. Lần đầu trên máy

```bash
python PE setup          # kiểm tra Python, ffmpeg, thư viện; tải font + model nhận diện mặt (~1 phút)
```
`setup` in dòng `THIẾU ...` kèm lệnh cài. **Với mỗi thứ thiếu: nói rõ nó là gì và để làm gì, hỏi người dùng đồng ý rồi mới chạy lệnh cài — không tự cài khi chưa hỏi.**
Lệnh thường gặp: `pip install -r <skill>/scripts/requirements.txt` · ffmpeg: Windows `winget install Gyan.FFmpeg`, macOS `brew install ffmpeg` · Python: `winget install Python.Python.3.12` / `brew install python`.
Sau khi cài xong, mở terminal mới nếu lệnh chưa nhận, chạy lại `setup` đến khi in `SẴN SÀNG ✔`.
Chưa chắc làm được không thì chạy demo: `python <skill>/examples/demo/make_demo.py` (tự sinh video thử, không cần tư liệu).

## 1. Quy trình chuẩn (làm đúng thứ tự, đừng nhảy cóc)

1. **Kiểm kê** — `ffprobe` source: phải **1080x1920**; ghi lại **fps** (30 hay 25, mọi mốc thời gian tính theo giây nên không lệch, nhưng phải biết).
   Liệt kê file minh họa người dùng đưa. Ảnh/clip nào là **màn hình có thông tin nhạy cảm** (API key, email, tên tài khoản, UI của sản phẩm
   người dùng không muốn lộ) thì **hỏi** trước khi dùng.
2. **Bóc băng** — `python PE transcribe source.mp4 --lang vi --prompt "<tên riêng, thuật ngữ>"` -> đọc `*.captions.draft.json`.
   Whisper hay nghe nhầm tên riêng: **tự đọc và sửa** rồi lưu `captions.json` (đừng đưa bản thô cho người dùng).
3. **Lên kế hoạch** — chia video thành cảnh theo ý của lời nói (xem §2 chọn kiểu). **Trình bày kế hoạch dạng bảng giây -> kiểu -> hình gì và chờ người dùng duyệt** rồi mới dựng.
4. **Viết `project.json`** (§3). Mốc thời gian lấy từ bước bóc băng (giây tuyệt đối).
5. **Xem thử rẻ trước khi render đủ**: `python PE sheet project.json --every 2.5` rồi **mở ảnh ra xem thật**; sửa; lặp lại.
   Muốn xem 1 đoạn chuyển động: `python PE render project.json --from 30 --to 45`.
6. **Render đủ** — `python PE render project.json` -> `out/final.mp4`.
7. **Caption** (nếu cần) — `python PE captions out/final.mp4 --segments captions.json --level --audit`. Đọc dòng `mặt chạm caption: N`; phải là 0.
8. **Bàn giao** — nói rõ file nằm đâu, và **nêu những gì bạn KHÔNG chắc** (chưa nghe âm thanh, chỗ nào nhận diện mặt có thể nhầm...).

## 2. Chọn kiểu cho từng đoạn

Mỗi cảnh có `layout`: `person` | `full` | `split` | `pip`. **Nhịp 10 giây**: không để quá ~10 giây mà hình không đổi (đổi cảnh, hoặc đổi minh họa).
**Đừng lặp 1 kiểu mãi** — xen kẽ. Không dùng đồ họa dày đặc cho câu nói ngắn dưới 2 giây.

| Muốn | Dùng | Ghi chú |
|---|---|---|
| Người nói, không đồ họa | `layout: person` | để thở giữa các cảnh đồ họa |
| Giải thích 1 ý bằng ảnh/clip, vẫn thấy người | `split` + `media` | minh họa nửa trên, người nửa dưới; tiêu đề tự thu nhỏ |
| Ý lớn / câu hỏi / con số | `full` + `title` (+ `counter`) | chiếm cả khung vài giây |
| Liệt kê 2-4 thứ, mỗi thứ nói 1 lần | `full` + `card_list` | mỗi thẻ pop đúng lúc nói tới (đặt `times` theo mốc từng chữ) |
| Giới thiệu nhân vật/sản phẩm lần lượt | `full` + `slides` | mỗi mục full khung, swipe sang mục kế |
| Hàng thẻ chân dung nhỏ | `cards` | 3 thẻ xếp ngang, có tên + phụ đề |
| Con số lớn đếm lên | `counter` | `value`, `prefix`, `suffix` |
| Minh họa 1 khái niệm trừu tượng | `sticker` | `kind`: xem `references/elements.md` |
| Clip dài chạy hết cảnh, vẫn muốn thấy người | `pip` | người nói thu nhỏ góc dưới phải |
| Cuối video / nhắc thương hiệu | `logo` | logo PNG nền trong |

**Nền**: `bg: light` (be) cho ý bình thường, `bg: dark` (hồng phấn) cho điểm nhấn/số liệu. Xen kẽ 2 nền, chuyển cảnh là 1 tấm màu quét ngang (tự thêm).
**Đổi màu**: `"theme": "xanh"` | `"tim-pastel"` | `"be-hong"` (mặc định) hoặc dict ghi đè — xem `references/theme.md`.

## 3. project.json

Mọi thời gian là **giây tuyệt đối của video**. Khoảng trống giữa các cảnh tự thành cảnh `person`.
Danh sách đầy đủ phần tử và tham số: `references/elements.md`. Ví dụ chạy được: `examples/demo/project.json` (sau khi chạy `make_demo.py`).

```json
{
  "source": "source.mp4",
  "out": "out/final.mp4",
  "theme": "be-hong",
  "audio": {"level": true, "sfx": true,
            "music": {"file": "nhac.mp3", "gain_db": -2, "beat_snap": false}},
  "scenes": [
    {"t": [1.6, 5.1], "layout": "split", "bg": "light", "elements": [
      {"type": "title", "lines": [["lead", "doanh nhân triệu view"], ["key", "Tên Người"]]},
      {"type": "media", "file": "assets/a.mp4", "t0": 0.5, "show": [1.8, 5.1], "tag": "Nguồn: ..."}]},
    {"t": [14.6, 19.6], "layout": "full", "bg": "dark", "elements": [
      {"type": "title", "lines": [["lead", "doanh thu"]], "y": 560},
      {"type": "counter", "value": 276, "prefix": "$", "at": 14.8}]}
  ]
}
```

## 4. Luật cứng (rút từ lần làm thật — vi phạm là hỏng video)

- **Không che mặt bằng đồ họa hay caption.** Caption do `captions` tự né; đồ họa của bạn thì tự kiểm bằng `sheet`/`stills`.
- **Mốc bắt theo lời nói, không theo cảm giác.** Pop-up danh sách phải trúng lúc nhắc từng mục (lấy giờ từ transcript có `word_timestamps`).
- **Số/tên/thông tin sự thật**: lấy từ lời người nói hoặc từ tư liệu người dùng đưa; **không tự bịa** (kể cả từ khoá trên thẻ — nếu tự nghĩ thì nói rõ cho người dùng biết).
- **Nội dung nhạy cảm trên màn hình** (tên sản phẩm bị cấm nhắc, key, email): không dùng ảnh chụp lộ ra; thay bằng sticker/chữ (`sticker`) hoặc crop bỏ phần đó, **và đổi cả chữ trong lời/caption** nếu người dùng yêu cầu.
- **Nguồn ảnh/clip của người khác**: luôn ghi `tag: "Nguồn: ..."` nhỏ dưới thẻ. Nhạc nền phải là nhạc **được phép dùng** (miễn phí/có ghi nguồn); đừng tự tải bài hit có bản quyền.
- **Tiếng**: luôn `audio.level = true` nếu người nói to nhỏ thất thường. Sau render **đo lại** (`python PE level` in số trước/sau) và nói thật là chưa nghe bằng tai.
- **Không báo "xong" khi chưa mở ảnh/bảng thu nhỏ ra xem.** Lỗi hay gặp: chữ tràn khung, thẻ đè mặt, mốc lệch lời, ảnh crop mất phần quan trọng.
- Người dùng chê/sửa 1 chỗ: mặc định chỉ áp cho video này; **hỏi** trước khi lưu thành quy tắc lâu dài.

## 5. Sự cố hay gặp

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| `Không mở được video nguồn` | sai đường dẫn; đường dẫn tương đối tính từ thư mục chứa `project.json` |
| Cảnh báo nguồn không phải 1080x1920 | `ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" out.mp4` |
| Caption nhảy lên cao / che mặt tay | nhận diện nhầm tay thành mặt; chạy `captions --audit`, xem `references/captions.md` |
| Tiếng nghe bị "bơm" | giảm `max_boost` trong `audio.level_voice` hoặc tắt `level` rồi nén tay |
| Đường dẫn có dấu tiếng Việt lỗi với OpenCV | skill đã xử lý ảnh (`np.fromfile`); nếu tự thêm code đọc ảnh, đừng dùng `cv2.imread` |
| Render chậm | 1 phút video ~ 5-6 phút render; dùng `--from/--to` và `sheet` để duyệt, chỉ render đủ 1 lần cuối |

## 6. Tài liệu kèm theo

- `references/elements.md` — mọi phần tử + tham số
- `references/layouts.md` — 4 bố cục, khi nào dùng, ảnh minh họa
- `references/captions.md` — cách caption né mặt hoạt động + cách kiểm
- `references/audio.md` — làm đều tiếng, SFX, nhạc nền, khớp nhịp
- `references/theme.md` — đổi màu
- `references/checklist.md` — checklist QC trước khi giao
