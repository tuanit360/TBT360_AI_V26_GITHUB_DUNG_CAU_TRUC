# TBT360 AI Quality Studio V67

Kế thừa V66, bổ sung chẩn đoán ảnh xác định được bằng PIL và panel kiểm tra ảnh riêng.

## Có thật trong V67
- Tab kiểm tra ảnh đơn lẻ, trả về độ phân giải, độ sáng trung bình, độ lệch chuẩn tương phản, proxy cạnh, tỷ lệ vùng gần đen/trắng và SHA256 pixel.
- Cảnh báo các trường hợp cần người xem lại (độ phân giải thấp, quá tối hoặc quá sáng, tương phản thấp).
- Ghi chẩn đoán cho từng ảnh sinh ra trong `generation.json` để so sánh có thể tái lập.
- Bộ test hồi quy chẩn đoán.
- Giữ nguyên khả năng build Portable CPU / CUDA từ V66.

## Giới hạn
Các chỉ số ảnh **không phải** thước đo độ đẹp, sharpness chuẩn, CLIP score, kiến trúc chính xác hoặc fidelity BIM. Không tích hợp ControlNet, SDXL, FLUX hay super-resolution AI. Chưa thực nghiệm trên GPU/Windows. Một ZIP nguồn không bao gồm checkpoint hoặc EXE; phải build thật trên Windows. Bước tiếp theo cải thiện hình học cần model/điều kiện inference và GPU phù hợp.

## Cách chạy
Trên máy build Windows có Python 3.11 x64: `BUILD_NVIDIA_WINDOWS_X64.bat` hoặc `BUILD_CPU_WINDOWS_X64.bat`, sau đó mang ZIP Portable được tạo sang máy đích. Để offline phải tải model trên máy build trước khi đóng gói.
