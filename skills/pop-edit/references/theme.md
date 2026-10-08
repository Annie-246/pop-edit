# Đổi màu

`"theme": "be-hong"` (mặc định) | `"xanh"` | `"tim-pastel"`, hoặc ghi đè từng màu (RGB):

```json
"theme": {"base": "be-hong", "accent": [20, 120, 90], "bg_dark": [200, 235, 215], "wipe": [60, 160, 120]}
```
Khoá màu: `bg_light grid_light dot_light bg_dark grid_dark dot_dark accent deep ink sel sel_dark wipe spike cream lead_light lead_dark small_light shadow plate sub_stroke` (xem `scripts/popedit/theme.py`).
Đổi theme xong chạy `python PE sheet project.json` để xem lại; chữ phải đọc rõ trên cả nền sáng lẫn nền đậm (kiểm bằng mắt).
