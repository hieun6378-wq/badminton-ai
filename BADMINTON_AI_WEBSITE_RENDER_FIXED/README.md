# Badminton AI Complete Website

Bản này chạy video thật: backend đọc video, chạy YOLO để nhận diện người, tìm ứng viên cầu, theo dõi quỹ đạo và tạo video output có khung PLAYER, khung SHUTTLE và km/h khi phát hiện pha smash. Mỗi sự kiện có clip riêng để bấm Xem lại.

## Cài đặt
Python 3.10+:
```
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Mở http://127.0.0.1:8000

Lần chạy đầu Ultralytics có thể tải model YOLO nhỏ `yolo11n.pt`.

## Lưu ý về đo tốc độ
Phần demo dùng detector người thật + detector cầu fallback dựa trên ảnh sáng. Đây là pipeline chạy video thật nhưng tốc độ chưa phải phép đo thể thao chuẩn. Để sản phẩm của bạn đạt độ tin cậy cao cần thay fallback bằng model shuttle đã train trên dữ liệu cầu lông và thêm model racket/contact + calibration camera. Hệ thống đã có điểm móc để thay các thành phần này.

Không nên coi số km/h của bản demo là số đo chính thức.


### Lưu ý video trình duyệt
Bản này tự chuyển video phân tích và clip smash sang H.264 (yuv420p, faststart) để Chrome/Edge/Safari phát được trực tiếp. Lần cài đầu sẽ tải thêm `imageio-ffmpeg`.
