# Hướng dẫn cho Claude trong repo này

Trao đổi với anh Khiêm bằng tiếng Việt.

## Quy trình tạo ảnh: chuyển cho ChatGPT, KHÔNG tự vẽ

Claude vẽ ảnh không đẹp. Vì vậy, mỗi khi task cần ảnh mới (ảnh minh họa, nhân vật, khung hình, thumbnail, banner, nền, logo...):

1. **KHÔNG** tự vẽ bằng SVG, PIL/Pillow, canvas, matplotlib hay code nào khác.
   Ngoại lệ: chỉnh sửa kỹ thuật trên ảnh có sẵn (cắt, resize, ghép, chèn chữ, làm video) thì vẫn tự làm bằng code như bình thường.
2. **Viết prompt** để anh dán vào ChatGPT (gói Plus, không dùng API). Trình bày theo mẫu bên dưới, đặt prompt trong một khối code để anh copy một lần là xong.
3. **Dừng lại và chờ** anh gửi ảnh. Nói rõ cần mấy ảnh, đặt tên file gì.
4. Khi nhận được ảnh:
   - Xem kỹ ảnh và so với yêu cầu: bố cục, nhân vật, màu, chữ có bị sai chính tả không, tỉ lệ khung hình, có lỗi AI kiểu tay sáu ngón hay chữ méo không.
   - Ảnh chưa đạt thì chỉ ra lỗi cụ thể và đưa **prompt sửa**, kiểu "giữ nguyên ảnh trên, chỉ đổi ...", để anh dán tiếp vào cùng cuộc chat ChatGPT.
   - Ảnh đạt thì lưu vào `assets/images/` với tên file rõ nghĩa (chữ thường, gạch dưới, không dấu) rồi dùng tiếp cho task.

### Mẫu trình bày prompt

> **Ảnh cần tạo:** <mô tả ngắn mục đích>
> **Tên file khi lưu:** `assets/images/<ten_file>.png`
>
> ```
> <prompt bằng tiếng Anh, chi tiết>
> ```
>
> *(Nếu cần: hướng dẫn thêm, ví dụ "đính kèm ảnh X vào ChatGPT trước khi dán prompt")*

### Cách viết prompt tốt

- Viết bằng **tiếng Anh**, vì ChatGPT tạo ảnh chính xác hơn. Chữ hiển thị trong ảnh thì giữ nguyên ngôn ngữ gốc, đặt trong ngoặc kép và ghi rõ là phải viết đúng chính tả.
- Nêu đủ: **chủ thể**, **hành động/tư thế**, **bối cảnh**, **phong cách** (ảnh thật, 3D Pixar, anime, flat vector...), **ánh sáng**, **màu chủ đạo**, **góc máy**, **tỉ lệ khung** (ví dụ 16:9 cho video, 9:16 cho TikTok/Reels, 1:1 cho avatar).
- Cần nhiều ảnh cùng một nhân vật thì mô tả nhân vật giống hệt nhau ở mọi prompt, và nhắc anh tạo các ảnh trong **cùng một cuộc chat ChatGPT** để giữ nhân vật nhất quán.
- Cần nền trong suốt thì ghi `transparent background, PNG`.
- Nêu rõ những thứ cần tránh, ví dụ `no text, no watermark`.
