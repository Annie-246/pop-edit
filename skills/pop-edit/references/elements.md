# Phần tử (element) trong `scenes[].elements`

Thời gian ở `show`, `at`, `times`, `hide_at` đều là **giây tuyệt đối của video**. Đường dẫn file tính từ thư mục chứa `project.json`.

## `title` — chữ tiêu đề
```json
{"type": "title", "lines": [["lead", "chữ dẫn nhỏ, nghiêng"], ["key", "Chữ chính"]], "y": 130, "show": [10, 14]}
```
- `lines`: danh sách `[kiểu, chữ]`. Kiểu: `lead` (nghiêng xám, nhỏ), `small` (rất nhỏ), `key` (đậm, **tự viết HOA**; dòng key cuối cùng có ô chọn chữ với 2 tay cầm).
- `y` (mặc định 130), `key_size` (118), `lead_size` (64). `show` = [bắt đầu, kết thúc]; bỏ `show` thì hiện cả cảnh.
- Chữ quá dài tự thu nhỏ vừa khung. Trong `split` tự thu nhỏ 24% và dời lên đỉnh.

## `media` — thẻ ảnh/clip
```json
{"type": "media", "file": "assets/a.mp4", "t0": 12.5, "crop": [x, y, w, h], "show": [3, 8], "tag": "Nguồn: ...", "box": [40, 440, 1000, 920]}
```
- `file`: ảnh (png/jpg/webp) hoặc video. Ảnh luôn đứng hình. Video **chạy bình thường từ giây `t0`** của file; muốn giữ nguyên 1 khung hình thì thêm `"freeze": true`.
- `crop`: cắt trước khi vào thẻ (px của file gốc) — dùng để bỏ phần thừa/nhạy cảm.
- `box`: vùng đặt thẻ (x, y, w, h). Trong `split` tự dùng khung trên.
- `tag`: dòng nguồn nhỏ dưới thẻ. `cover: true` để phủ kín thẻ (cắt bớt) thay vì vừa khung.

## `counter` — số đếm lên
`{"type":"counter","value":276,"prefix":"$","suffix":"","at":14.8,"dur":1.4,"y":640,"size":330,"decimals":0}`

## `card_list` — danh sách thẻ pop-up theo lời nói
```json
{"type":"card_list","times":[31.1,31.7,32.2],"hide_at":33.0,"items":[
  {"label":"Sức khỏe","icon":"health","chips":["thảo dược","sống thọ"]},
  {"label":"Tài chính","icon":"money","chips":["đầu tư"]},
  {"label":"Quan hệ","icon":"love","chips":["hẹn hò"]}]}
```
`times[i]` = giây thẻ i bật lên (lấy từ lúc người nói nhắc mục i). Tối đa 3 thẻ vừa khung cao 450-1400.

## `cards` — hàng thẻ chân dung (2-4 thẻ)
`{"type":"cards","at":59.6,"stagger":0.45,"items":[{"file":"a.png","name":"Ann","sub":"28 tuổi"}, ...]}`

## `slides` — mỗi mục full khung, swipe sang mục kế
`{"type":"slides","header":"Bước 3","items":[{"file":"a.mp4","t0":10,"crop":[...],"name":"Amos","sub":"101 tuổi"}, ...]}`
Thời lượng cảnh chia đều cho các mục. Mỗi mục là ảnh hoặc clip, tự phủ kín 1080x1920 (cắt giữa).

## `sticker` — sticker vẽ sẵn
`{"type":"sticker","kind":"robot","x":880,"y":1420,"size":200,"at":36,"tilt":-8}`
`kind`: `health money love star bolt chat check target bulb book robot script`. Dùng thay cho ảnh chụp giao diện không muốn lộ.

## `logo`
`{"type":"logo","file":"assets/logo.png","y":900,"width":900,"at":195}` — PNG nền trong.

## Cảnh
```json
{"t":[a,b], "layout":"person|full|split|pip", "bg":"light|dark", "elements":[...],
 "pip":{"pos":"bottom-right|bottom-left|bottom-center","w":400,"shape":"rounded|circle"}}
```
- `split`: nửa trên đồ họa, nửa dưới người nói (cắt từ hàng `split_crop_y` của source, mặc định 130 — chỉnh ở gốc `project.json` nếu đầu người bị cắt).
- `pip`: người nói thu nhỏ ở góc dưới; dùng khi đồ họa/clip cần cả khung.
