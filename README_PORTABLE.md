# BIM AI Kiến Trúc 360 V171 — BIMAI360 Windows x64

Ứng dụng hiển thị: **BIM AI Kiến Trúc 360**. Tên dùng để lưu/chạy offline: **BIMAI360**.

Giải nén toàn bộ `BIMAI360_V171_PORTABLE_WINDOWS_X64_CPU.zip` vào một thư mục mới, ví dụ `C:\BIMAI360`. Mở `BIMAI360.exe` hoặc `START_BIMAI360_DIAGNOSTIC.bat` nếu cần ghi log. Không chạy ngay trong ZIP, không chỉ sao chép EXE.

Dữ liệu dự án trong các thư mục `dataset`, `models`, `loras`, `output` vẫn giữ nguyên cấu trúc, không tự xóa hoặc thay đổi dữ liệu TBT360 AI cũ. Nếu đã có dữ liệu trong bộ cũ, **sao chép thủ công các thư mục dữ liệu** vào bộ BIMAI360 mới sau khi kiểm tra bản sao lưu. Không ghi đè trực tiếp lên bản cũ.

Tại một màn hình, sử dụng **NẠP ẢNH HUẤN LUYỆN**, kiểm tra ảnh, crop, QA và xuất tham chiếu BIM. Nhập ảnh chỉ lưu và gắn nhãn nháp; không được coi là đã huấn luyện LoRA. Muốn sinh ảnh offline phải có mô hình SD1.5 được tải hợp lệ trong `models/sd15`; không kèm model weights. Bản CPU có thể sinh ảnh chậm. IFC/RVT chưa được xuất trực tiếp từ ảnh vì cần mô hình BIM ngữ nghĩa có hình học, kích thước và xác minh thực tế.

Bộ file cần chạy: `BIMAI360.exe`, `_internal`, README, launcher, manifest/checksums. GitHub Actions kiểm thử khởi động giao diện local trước khi xuất artifact.

Batch V97–V171: hardened canonical BIM handoff with immutable entity updates, host/level checks, deterministic SHA-256 fingerprints and one-screen validation. BIM geometry/IFC certification not claimed. Five internal checkpoints, one consolidated PR and artifact.

V102–V171: canonical BIM command history with safe update/undo/redo, no-op and failed edit isolation, shared source of 2D/3D BIM data. No claim of IFC geometry export or user-image LoRA training. One PR and artifact for all five internal milestones.

Batch V107–V171 adds atomic saving and SHA256-verified reopening for canonical BIM JSON. This feature is the data layer only, not a viewport BIM editor or IFC exporter. Five internal milestones produce one PR/ZIP.

V112–V171 adds project-scoped architecture image observation, roles for perspective/plan/elevation/section, image SHA256 and multiview verification groundwork. No trained ML checkpoint or semantic inference is bundled. Five milestones produce one PR and ZIP.

V117–V171 adds a rectangular schematic building shell parameterized by width/depth/floor height/level count, sharing canonical wall IDs between SVG plan/elevation and JSON geometry. This is an editable concept handoff, not image-inferred plans, technical MEP, full 3D renderer or certified IFC.

V122–V171 extends the same explicitly dimensioned rectangular BIM concept shell to front/rear/left/right elevations and two schematic sections. Diagrams do not infer rooms, roof construction, stairs, MEP or IFC, nor do they constitute a technical model.

V127–V171 exports a schematic plan as ASCII DXF (meter units, wall baseline LINE entities in level-specific layers), based on the same user-dimensioned canonical shell and SVG elevations/sections. DXF is editable 2D reference linework, not full architectural BIM, technical MEP or IFC. Five checkpoints produce one PR/ZIP.

V132–V171 adds a simple deterministic 55/45 two-zone conceptual floorplate based on user-entered size. Canonical space entities, shared wall partition and SVG drawing use the same dimensions; no AI room detection, opening placement, MEP or technical compliance is claimed.

V137–V171 validates conceptual room extents, partition alignment and floorplate area directly from the canonical BIM model. Windows CI now uses non-failing teardown after successful HTTP readiness. No technical architecture/MEP/IFC capability is inferred from the test.

V142–V171 includes an optional local CUDA Vision2Seq model inference interface. Users must supply a compatible model checkpoint; the CPU Windows Portable build does not contain trained architecture VLM weights and cannot execute CUDA inference without a suitable GPU/runtime. Descriptions are unverified AI suggestions and do not imply semantic BIM geometry, IFC, or technical compliance.

V147–V171 upgrades the existing VLM path to strict architecture observation JSON with visible evidence/uncertainty for building type, apparent floors, roof and facade. Inference failures and malformed model output are blocked. Only after explicit user confirmation of dimensions does the UI permit canonical schematic BIM handoff. Image inference does not determine metric dimensions or IFC-ready geometry. A real compatible locally provided CUDA model is needed; no checkpoint is bundled.

V152–V171 adds VLM cross-image evidence reconciliation. Upload up to 12 VLM JSON observations for one project to review consistent/contradictory building, apparent floor, roof and facade claims. Only actual completed locally run VLM records can be compared. Agreement does not prove metric dimensions, engineering compliance, or IFC-ready BIM.

V157–V171 upgrades the existing multiview VLM pipeline with an explicit design-approval gate before canonical concept BIM generation. The software rejects tampered consensus records and unresolved AI conflicts; it records per-image SHA256 fingerprints and the user-approved dimensions. No claim of photo-inferred metric dimensions, trained models bundled, technical MEP or IFC export.

V162–V171 extends evidence-gated multiview BIM approval with an advisory-only architectural review and reproducible verified checksum comparison. VLM observations never directly generate metric geometry: confirmed dimensions are mandatory. No trained checkpoint, image-to-BIM geometry synthesis, true IFC exporter or technical MEP is claimed.

Batch V167–V171 adds geometric wall mesh extrusion directly from canonical wall baselines and exports a real glTF binary (schematic_walls.glb) with a mapping file of canonical wall IDs. The geometric source is explicitly entered dimensions. The output remains a conceptual rectangular shell, not reconstructed from photography; no IFC, detailed spaces/MEP or engineering certification. GLB exporter uses trimesh and is tested for mesh reopening.
