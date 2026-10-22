# BIM AI Kiến Trúc 360 V96 — BIMAI360

Đây là mã nguồn ứng dụng AI kiến trúc / chuẩn bị dữ liệu BIM, kế thừa chức năng TBT360 AI V78–V91. Tên hiển thị là **BIM AI Kiến Trúc 360**; tên offline là **BIMAI360**.

- Chạy `BIMAI360.exe` trong gói Windows Portable đã PASS CI, không yêu cầu cài Python trên máy đích.
- Nạp ảnh/ZIP và kiểm tra dataset trên một màn hình.
- Crop board, kiểm tra biên và xuất gói ảnh/JSON tham chiếu CAD/BIM.
- Canonical BIM handoff có kiểm tra level, ID, host và tọa độ nhưng **chưa phải IFC hay BIM kỹ thuật hoàn chỉnh**.
- LoRA chưa được chứng minh đã huấn luyện trên ảnh người dùng; cần GPU, dữ liệu được duyệt, checkpoint và đánh giá thực.

Các thư mục dataset/models/loras/output của phiên bản cũ chỉ được tái sử dụng khi người dùng chép vào bộ mới và giữ bản sao lưu.
