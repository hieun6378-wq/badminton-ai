# BADMINTON AI — Deploy website không cần chạy CMD

Bản này giữ nguyên phần AI phân tích video của bản V2 H.264.
Chỉ bổ sung cấu hình Docker/Render để chạy backend AI trên máy chủ.

## Cách triển khai

1. Tạo tài khoản Render.
2. Tạo một GitHub repository mới, ví dụ `badminton-ai`.
3. Upload toàn bộ các file/thư mục trong gói này lên repository.
4. Trên Render chọn **New → Web Service**.
5. Chọn repository `badminton-ai`.
6. Render sẽ nhận `Dockerfile` và tự build.
7. Sau khi Deploy xong, Render cấp cho bạn một địa chỉ dạng:
   `https://ten-app.onrender.com`
8. Mở địa chỉ đó bằng Chrome. Không cần mở CMD trên máy người dùng.

## Lưu ý

- Máy chủ cần CPU/RAM đủ để chạy OpenCV + YOLO; video dài hoặc độ phân giải cao sẽ cần nhiều thời gian.
- File video/output trên gói cơ bản có thể là dữ liệu tạm thời. Nếu cần lưu video lâu dài, nên thêm kho lưu trữ riêng.
- Đây vẫn là hệ AI hiện tại của bản V2: tốc độ là ước lượng từ video, không phải máy đo tốc độ BWF chuyên nghiệp.
