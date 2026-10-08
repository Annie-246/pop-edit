# Caption né mặt

```bash
python PE transcribe video.mp4 --lang vi --prompt "tên riêng, thuật ngữ"   # -> video.captions.draft.json
# Claude đọc + SỬA lỗi nghe nhầm -> lưu captions.json  (giữ nguyên start/end)
python PE captions video.mp4 --segments captions.json --level --audit
```
`captions.json`: `[{"start": 0.0, "end": 4.5, "text": "Câu đã sửa"}, ...]` (start/end = lúc nói chữ đầu/chữ cuối).

## Cách hoạt động
1. Quét video 6 mẫu/giây: vị trí mặt (YuNet) + đường chia đôi (nếu có).
2. Lọc nhận nhầm (bàn tay, hình nền): bỏ hộp quá nhỏ, bỏ hộp điểm thấp không có hộp tin cậy ở khung lân cận.
3. Chia câu thành cụm tối đa ~6 từ, 1-2 dòng, rồi **mỗi cụm tự chọn vị trí**:
   - mặc định: giữa khung, y=1500 (dưới ngực);
   - bố cục chia đôi (có chỗ trống): **ngay dưới khung đồ họa phía trên, trên đường chia** — không đè tóc;
   - nếu chạm mặt: dời lên/xuống theo bước 20px, rồi thử lệch trái/phải; mọi vị trí đều phải cách mặt >= 34px.
   - nếu cả vùng dưới đều kín thì mới thử vùng trên (y 260-700).
4. Bố cục đổi giữa chừng 1 cụm -> cắt cụm tại **đúng khung hình** đổi (dò từng khung), và **ẩn caption ~0,1s** ngay lúc đổi để không bao giờ đè mặt khi hình đang chuyển.
5. `--audit` quét lại **video đã in** và đếm khung nào còn mặt chạm chữ.

## Giới hạn (nói thật với người dùng)
- Chữ **có thể che cổ, ngực, tay** — chỉ cam kết không che **mặt**.
- Nhận diện mặt có thể nhầm bàn tay thành mặt (làm caption bị dời không cần thiết) hoặc bỏ sót mặt nghiêng/che. `--audit` chỉ đếm mặt MÀ NHẬN DIỆN THẤY.
- Caption chia thời gian theo từng **câu**, không bám từng chữ -> lệch vài phần mười giây so với lúc nói.
