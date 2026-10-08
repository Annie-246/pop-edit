# pop-edit

**Skill cho [Claude Code](https://claude.ai/code): biến video quay mặt thành video dọc 9:16 có tiêu đề, ảnh minh họa pop-up, SFX, nhạc nền và phụ đề tự né mặt — chỉ bằng cách trò chuyện.**

![demo](docs/demo.gif)

<sub>Kết quả thật (cắt từ 1 video đã dựng bằng skill) · [xem bản có tiếng: docs/demo.mp4](docs/demo.mp4) · Ảnh/clip của Mark Tilbury trong video là tư liệu tham khảo, có ghi nguồn.</sub>

## Cài đặt — chỉ 1 bước

Mở Claude Code (trong thư mục chứa video của bạn) rồi **dán link này và nói**:

> Cài giúp mình skill này: https://github.com/Annie-246/pop-edit

Xong. Claude tự tải và cài skill. Nếu máy thiếu công cụ nào (Python, ffmpeg, thư viện…), Claude sẽ **báo và hỏi bạn có đồng ý cài không** rồi cài giúp. Chưa có Claude Code thì xem [hướng dẫn PDF](docs/HUONG-DAN.pdf) (2 phút).

## Dùng

Bỏ vào 1 thư mục: video quay mặt dọc `source.mp4` (1080×1920) + ảnh/clip minh họa. Mở Claude Code trong thư mục đó và nói:

> Dựng video này bằng skill pop-edit. Chưa dựng vội, đưa mình bảng kế hoạch giây → kiểu → hình gì để mình duyệt.

Claude bóc băng, đề xuất kế hoạch, chờ bạn duyệt, xem thử bằng ảnh thu nhỏ rồi mới render. Muốn thêm phụ đề: *"Chèn phụ đề, né mặt, làm đều tiếng."* Muốn đổi: *"đoạn 24–31s chuyển sang full màn hình"*, *"đổi tone xanh dương"*, *"thêm nhạc nền này"*.

📘 Hướng dẫn có hình: [`docs/HUONG-DAN.pdf`](docs/HUONG-DAN.pdf)

## Có gì trong skill

| | |
|---|---|
| Bố cục | người nói full · **chia đôi** (minh họa trên, người dưới) · đồ họa full · **PiP** (người thu nhỏ ở góc) |
| Chữ | tiêu đề đậm có **ô chọn chữ**, chữ dẫn nghiêng, nền lưới + chấm |
| Phần tử | thẻ ảnh/clip bật lên · **danh sách pop-up theo lời nói** · số đếm lên · sticker vector · nhân vật full khung **swipe** · hàng thẻ chân dung · logo |
| Âm thanh | **làm đều tiếng nói** · SFX tự tổng hợp (không bản quyền) · nhạc nền hạ khi có lời · khớp chuyển cảnh theo nhịp (tuỳ chọn) |
| Caption | bóc băng Whisper → Claude sửa lỗi → **tự đặt chỗ né mặt** → kiểm tra lại video đã in |
| Màu | `be-hong` (mặc định), `xanh`, `tim-pastel`, hoặc tự đặt |

## Giới hạn (nói thật)

- Chỉ nhận video **dọc 1080×1920**. Dựng chậm: khoảng 4–6 phút cho mỗi phút video (chạy bằng CPU).
- Caption **không che mặt** nhưng có thể che cổ/ngực/tay. Nhận diện mặt có thể nhầm bàn tay hoặc bỏ sót mặt nghiêng.
- Âm thanh được **đo bằng máy**, không được nghe bằng tai — hãy nghe lại trước khi đăng.
- Ảnh/clip của người khác và nhạc nền: bạn chịu trách nhiệm về bản quyền; skill nhắc ghi nguồn nhưng không kiểm tra giúp bạn.

## Cách khác để cài

- Marketplace (gõ trong Claude Code): `/plugin marketplace add Annie-246/pop-edit` rồi `/plugin install pop-edit@pop-edit`
- Chép tay: tải repo, chép thư mục `skills/pop-edit` vào `~/.claude/skills/` (Windows: `C:\Users\<tên>\.claude\skills\`).

## Dành cho Claude Code — khi người dùng gửi link repo này và nhờ cài skill

Làm đúng thứ tự, **báo người dùng từng bước bằng tiếng Việt, ngắn gọn**:

1. Tải về thư mục tạm: `git clone --depth 1 https://github.com/Annie-246/pop-edit <thư-mục-tạm>` (không có `git` thì tải ZIP của repo).
2. Chép `skills/pop-edit` vào **thư mục skill cá nhân**: `~/.claude/skills/pop-edit` (Windows: `%USERPROFILE%\.claude\skills\pop-edit`). Nếu thư mục đã có, hỏi người dùng có ghi đè (cập nhật) không.
3. Chạy `python <đường-dẫn>/pop-edit/scripts/popedit.py setup`. Nó liệt kê dòng `THIẾU …` kèm lệnh cài. Với **mỗi thứ thiếu**: nói rõ nó là gì và để làm gì, **hỏi người dùng đồng ý rồi mới chạy** lệnh cài (`pip install -r …/requirements.txt`; ffmpeg: `winget install Gyan.FFmpeg` hoặc `brew install ffmpeg`; chưa có Python: `winget install Python.Python.3.12` hoặc `brew install python`). **Không tự cài khi chưa hỏi.** Sau khi cài, đóng/mở lại terminal nếu lệnh chưa nhận, rồi chạy lại `setup` đến khi in `SẴN SÀNG ✔`.
4. Xoá thư mục tạm. Báo người dùng skill đã sẵn sàng; nếu `pop-edit` chưa xuất hiện trong danh sách skill thì bảo họ khởi động lại Claude Code.
5. Hỏi người dùng muốn **chạy thử demo** không (`examples/demo/make_demo.py` rồi `render`, không cần tư liệu) hay dựng luôn video thật.

## Cấu trúc

```
.claude-plugin/        manifest để cài qua marketplace
skills/pop-edit/
  SKILL.md             hướng dẫn cho Claude (quy trình, luật cứng, sự cố)
  scripts/popedit/     engine, timeline, render, captions, faces, audio, sfx
  references/          phần tử, bố cục, caption, âm thanh, theme, checklist
  examples/demo/       bộ demo tự sinh
docs/                  HUONG-DAN.pdf, demo.mp4/gif, mã nguồn dựng PDF
```

## Giấy phép

MIT (xem [LICENSE](LICENSE)). Font *Bricolage Grotesque* và *Plus Jakarta Sans* (OFL) và model nhận diện mặt *YuNet* của OpenCV (MIT) được tải về khi chạy `setup`, không nằm trong repo.
