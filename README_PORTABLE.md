# BIM AI Kiến Trúc 360 V131 — BIMAI360 Windows x64

Ứng dụng hiển thị: **BIM AI Kiến Trúc 360**. Tên dùng để lưu/chạy offline: **BIMAI360**.

Giải nén toàn bộ `BIMAI360_V131_PORTABLE_WINDOWS_X64_CPU.zip` vào một thư mục mới, ví dụ `C:\BIMAI360`. Mở `BIMAI360.exe` hoặc `START_BIMAI360_DIAGNOSTIC.bat` nếu cần ghi log. Không chạy ngay trong ZIP, không chỉ sao chép EXE.

Dữ liệu dự án trong các thư mục `dataset`, `models`, `loras`, `output` vẫn giữ nguyên cấu trúc, không tự xóa hoặc thay đổi dữ liệu TBT360 AI cũ. Nếu đã có dữ liệu trong bộ cũ, **sao chép thủ công các thư mục dữ liệu** vào bộ BIMAI360 mới sau khi kiểm tra bản sao lưu. Không ghi đè trực tiếp lên bản cũ.

Tại một màn hình, sử dụng **NẠP ẢNH HUẤN LUYỆN**, kiểm tra ảnh, crop, QA và xuất tham chiếu BIM. Nhập ảnh chỉ lưu và gắn nhãn nháp; không được coi là đã huấn luyện LoRA. Muốn sinh ảnh offline phải có mô hình SD1.5 được tải hợp lệ trong `models/sd15`; không kèm model weights. Bản CPU có thể sinh ảnh chậm. IFC/RVT chưa được xuất trực tiếp từ ảnh vì cần mô hình BIM ngữ nghĩa có hình học, kích thước và xác minh thực tế.

Bộ file cần chạy: `BIMAI360.exe`, `_internal`, README, launcher, manifest/checksums. GitHub Actions kiểm thử khởi động giao diện local trước khi xuất artifact.

Batch V97–V131: hardened canonical BIM handoff with immutable entity updates, host/level checks, deterministic SHA-256 fingerprints and one-screen validation. BIM geometry/IFC certification not claimed. Five internal checkpoints, one consolidated PR and artifact.

V102–V131: canonical BIM command history with safe update/undo/redo, no-op and failed edit isolation, shared source of 2D/3D BIM data. No claim of IFC geometry export or user-image LoRA training. One PR and artifact for all five internal milestones.

Batch V107–V131 adds atomic saving and SHA256-verified reopening for canonical BIM JSON. This feature is the data layer only, not a viewport BIM editor or IFC exporter. Five internal milestones produce one PR/ZIP.

V112–V131 adds project-scoped architecture image observation, roles for perspective/plan/elevation/section, image SHA256 and multiview verification groundwork. No trained ML checkpoint or semantic inference is bundled. Five milestones produce one PR and ZIP.

V117–V131 adds a rectangular schematic building shell parameterized by width/depth/floor height/level count, sharing canonical wall IDs between SVG plan/elevation and JSON geometry. This is an editable concept handoff, not image-inferred plans, technical MEP, full 3D renderer or certified IFC.

V122–V131 extends the same explicitly dimensioned rectangular BIM concept shell to front/rear/left/right elevations and two schematic sections. Diagrams do not infer rooms, roof construction, stairs, MEP or IFC, nor do they constitute a technical model.

V127–V131 exports a schematic plan as ASCII DXF (meter units, wall baseline LINE entities in level-specific layers), based on the same user-dimensioned canonical shell and SVG elevations/sections. DXF is editable 2D reference linework, not full architectural BIM, technical MEP or IFC. Five checkpoints produce one PR/ZIP.
