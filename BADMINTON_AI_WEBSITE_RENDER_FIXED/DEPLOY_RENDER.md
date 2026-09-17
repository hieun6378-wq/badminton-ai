# BADMINTON AI — Bản Docker/Render đã sửa

Bản này giữ nguyên phần AI phân tích video và giao diện của bản hiện tại.
Chỉ sửa cấu hình máy chủ để Docker/Render chạy đúng cổng và đúng module FastAPI.

## Triển khai không cần CMD trên máy người dùng

1. Giải nén ZIP.
2. Đưa toàn bộ file/thư mục bên trong lên một GitHub repository, ví dụ `badminton-ai`.
3. Vào Render → New → Web Service.
4. Chọn repository GitHub.
5. Chọn Runtime/Language là Docker nếu Render hỏi.
6. Nhấn Create Web Service / Deploy.
7. Khi build thành công, mở địa chỉ `https://...onrender.com`.

Dockerfile đã dùng `PORT` mà Render cấp (mặc định 10000) và chạy `main:app` từ thư mục backend.

## Lưu ý

- AI vẫn là hệ AI hiện tại: tốc độ được ước lượng từ video, chưa phải máy đo tốc độ BWF chuyên nghiệp.
- Video được xử lý trên máy chủ nên video dài/nặng có thể mất thời gian và cần đủ CPU/RAM.
- File trong ổ đĩa của web service có thể là dữ liệu tạm; nếu cần lưu video lâu dài nên dùng storage riêng.
