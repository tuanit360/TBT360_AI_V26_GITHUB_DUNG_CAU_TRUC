# V68 Advanced ML Studio — mức hỗ trợ thực tế

## V67 có phải học máy không?
Có. SD1.5 là mô hình diffusion pretrained dùng suy luận, và `training/run_lora.py` có mã chạy LoRA training thực trên CUDA. Tuy nhiên **không tìm thấy checkpoint huấn luyện đã hoàn tất trong source**; bộ source không chứa model weights. Vì vậy không tuyên bố đã học tập dữ liệu riêng hoặc mô hình đạt độ chính xác cụ thể.

## V68 bổ sung
- Tab nâng cao thực thi tùy chọn SDXL 1.0 và SD1.5 img2img với checkpoint HuggingFace.
- ControlNet Canny theo đúng family model; cần opencv-python-headless.
- Diffusion x4 upscaler từ checkpoint riêng, khác phóng Lanczos; ảnh AI có thể thay đổi chi tiết công trình.
- Audit dữ liệu có dHash gần trùng để phát hiện nguy cơ lặp dữ liệu/overfit; **không phải bằng chứng hết overfit**.
- GPU offload, giới hạn ảnh để giảm nguy cơ OOM, seed và metadata đầu ra.

## Điều kiện để chạy
Máy build có Python 3.11 Windows x64, GPU NVIDIA và torch CUDA phù hợp. `BUILD_NVIDIA_WINDOWS_X64.bat` build bộ phổ thông; với ControlNet, cài `requirements_advanced.txt` trên máy build trước khi đóng gói. Nếu offline phải tự tải model SDXL, ControlNet và x4 vào `models/sdxl`, `models/control_sd15`, `models/control_sdxl`, `models/x4_upscaler`. Tuân thủ license và quyền truy cập từng checkpoint; dung lượng nhiều GB.

Chưa chạy thử tải weights, CUDA, inference hay đóng gói exe trên Windows trong môi trường hiện tại. Các chức năng mới có implementation và kiểm tra tĩnh nhưng **chưa xác nhận hoạt động end-to-end**. Không tự khẳng định tăng chất lượng đo được hay hiểu BIM.
