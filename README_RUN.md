# TBT360 AI V65 — BỘ CÀI WINDOWS SỬA LỖI PYTHON

Đã sửa lỗi: Python installer báo exit=0 nhưng không có `runtime\Python311\python.exe`.
Nguyên nhân nghi ngờ là cách truyền `TargetDir` với đường dẫn có khoảng trắng/Unicode qua PowerShell `Start-Process`.

## Cài đặt
1. Giải nén **toàn bộ** ZIP vào thư mục ngắn dễ ghi, ví dụ `C:\TBT360_AI_V65` (không chạy trực tiếp bên trong ZIP).
2. Bấm đúp `CHAY_TBT360_AI_WINDOWS.bat` hoặc `CAI_DAT_VA_CHAY.bat`.
3. Máy cần **Windows x64**, Internet và khoảng **15–25 GB** dung lượng còn trống. Trình cài sẽ tải Python 3.11.9, PyTorch, thư viện AI và (khi dùng) model AI. **Đây là bộ cài online; không kèm sẵn model/LoRA.**
4. Lần sau chạy lại BAT; venv được tái sử dụng.

## Nếu máy đã gặp lỗi từ bản trước
Nên giải nén ZIP mới vào **thư mục mới** để tránh trộn script cũ. Không xóa thư mục dữ liệu/model cá nhân.
Kiểm tra `logs\bootstrap.log`, `logs\python-installer.log`, `logs\check_stdout.json` khi gặp lỗi.

## Giới hạn
Script, cú pháp Python và nội dung ZIP được kiểm tra trong môi trường Linux; **chưa thể thực chạy trình cài hoặc kiểm chứng GPU/Windows trên máy của bạn**.
LoRA riêng và trọng số diffusion **không có sẵn**; không cam kết NVIDIA GPU ít VRAM sẽ huấn luyện được.
