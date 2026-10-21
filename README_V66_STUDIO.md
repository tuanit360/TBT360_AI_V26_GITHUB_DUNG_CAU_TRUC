# TBT360 AI Studio V66 — nâng cấp trên V65

## Điểm mới thực hiện
- Giao diện Gradio 3 tab, hướng trọng tâm viewport gallery, các tham số nâng cao trong accordion.
- Preset xem nhanh/cân bằng/chi tiết/sáng tạo, phong cách kiến trúc/nội thất/ngoại thất.
- Điều khiển CFG, steps, preservation, LoRA, batch seed và quản lý VRAM.
- Hậu xử lý Lanczos 1x/2x/4x + Unsharp Mask, có ghi rõ KHÔNG phải AI super resolution.
- Export manifest JSON có cấu hình, seed và metadata tái lập; progress có kiểm soát.
- GPU mode cân bằng sử dụng CUDA trực tiếp để ưu tiên tốc độ; low-VRAM dùng sequential CPU offload.

## Chạy và build
Theo README_START_HERE.md và README_PORTABLE.md. Trên Windows build, chạy BUILD_CPU_WINDOWS_X64.bat hoặc BUILD_NVIDIA_WINDOWS_X64.bat. Đóng gói bằng PyInstaller và tự kiểm tra. Máy đích không cần cài Python nếu build thành công và mọi runtime phụ thuộc đã được gom vào ZIP.

## Giới hạn kiểm chứng
Chưa build và đo FPS, throughput, VRAM hoặc quality metrics trên Windows/GPU thực tế. SD1.5 nền 512px không đạt chất lượng cao nhất của các model lớn hơn. Chưa có AI upscaler, ControlNet hay pipeline huấn luyện SDXL/Flux; không được hiểu là đã có. Không có trọng số model trong source nhỏ này.
