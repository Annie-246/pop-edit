# Âm thanh

## Làm đều tiếng nói (`audio.level: true` hoặc `python PE level video.mp4`)
Người quay tự do hay nói lúc to lúc nhỏ (đo thật trên 1 video 2,5 phút: mức nói dao động từ -17 dB đến -7 dB, đỉnh vượt 0 dB gây méo).
Cách làm: đo mức nói cục bộ (cửa sổ ±2,5s, lấy phần to của lời nói) -> đường cong gain mượt (cắt tối đa 9 dB, tăng tối đa 11 dB) -> nén nhẹ -> chuẩn hoá -> chặn đỉnh.
Kết quả mẫu: độ lệch 2,05 dB -> 0,78 dB, đỉnh +3 dBFS -> 0 dBFS. Chỉ chỉnh độ to, không cắt/đổi gì khác.
**Luôn in số trước/sau cho người dùng** và nói rõ là chưa nghe bằng tai.

## SFX (`audio.sfx: true`)
Tự tổng hợp bằng numpy (không dính bản quyền): `whoosh` (chuyển cảnh), `pop` (thẻ/sticker bật), `swipe` (đổi nhân vật), `impact` (số đếm xong).
Đặt sớm hơn hình ~0,08s. Đỉnh SFX mặc định -14 dBFS (`audio.sfx_peak_db`); nếu giọng nói to thì SFX hầu như chìm — tăng lên -10.
Liều lượng: video ~2,5 phút -> ~50 điểm là vừa. Đừng thêm SFX cho từng chữ.

## Nhạc nền (`audio.music`)
`{"file":"nhac.mp3","gain_db":-2,"beat_snap":true}`
- Tự lặp (crossfade 3s), hạ xuống khi có lời (sidechain), vào/ra mượt.
- `beat_snap` (cần `pip install librosa`): chọn tốc độ nhạc (±8%) + điểm bắt đầu sao cho các chuyển cảnh rơi gần nhịp nhất, mỗi mốc nhích tối đa 0,22s. Trên video mẫu 32 mốc, ~16 mốc trong 0,1s của nhịp.
- **Bản quyền**: chỉ dùng nhạc được phép (Bensound có ghi nguồn, nhạc người dùng tự có). Đừng tự tải bài hit.
- Mức nhạc: nhỏ hơn giọng ~12 dB là vừa. Nhạc quá nhỏ thì người dùng sẽ báo "không nghe thấy gì" — **đo lại** sau khi trộn.
