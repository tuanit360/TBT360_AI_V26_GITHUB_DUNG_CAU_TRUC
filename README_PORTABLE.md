# BIM AI Kiến Trúc 360 V266 — BIMAI360 Windows x64

Ứng dụng hiển thị: **BIM AI Kiến Trúc 360**. Tên dùng để lưu/chạy offline: **BIMAI360**.

Giải nén toàn bộ `BIMAI360_V266_PORTABLE_WINDOWS_X64_CPU.zip` vào một thư mục mới, ví dụ `C:\BIMAI360`. Mở `BIMAI360.exe` hoặc `START_BIMAI360_DIAGNOSTIC.bat` nếu cần ghi log. Không chạy ngay trong ZIP, không chỉ sao chép EXE.

Dữ liệu dự án trong các thư mục `dataset`, `models`, `loras`, `output` vẫn giữ nguyên cấu trúc, không tự xóa hoặc thay đổi dữ liệu TBT360 AI cũ. Nếu đã có dữ liệu trong bộ cũ, **sao chép thủ công các thư mục dữ liệu** vào bộ BIMAI360 mới sau khi kiểm tra bản sao lưu. Không ghi đè trực tiếp lên bản cũ.

Tại một màn hình, sử dụng **NẠP ẢNH HUẤN LUYỆN**, kiểm tra ảnh, crop, QA và xuất tham chiếu BIM. Nhập ảnh chỉ lưu và gắn nhãn nháp; không được coi là đã huấn luyện LoRA. Muốn sinh ảnh offline phải có mô hình SD1.5 được tải hợp lệ trong `models/sd15`; không kèm model weights. Bản CPU có thể sinh ảnh chậm. IFC/RVT chưa được xuất trực tiếp từ ảnh vì cần mô hình BIM ngữ nghĩa có hình học, kích thước và xác minh thực tế.

Bộ file cần chạy: `BIMAI360.exe`, `_internal`, README, launcher, manifest/checksums. GitHub Actions kiểm thử khởi động giao diện local trước khi xuất artifact.

Batch V97–V266: hardened canonical BIM handoff with immutable entity updates, host/level checks, deterministic SHA-256 fingerprints and one-screen validation. BIM geometry/IFC certification not claimed. Five internal checkpoints, one consolidated PR and artifact.

V102–V266: canonical BIM command history with safe update/undo/redo, no-op and failed edit isolation, shared source of 2D/3D BIM data. No claim of IFC geometry export or user-image LoRA training. One PR and artifact for all five internal milestones.

Batch V107–V266 adds atomic saving and SHA256-verified reopening for canonical BIM JSON. This feature is the data layer only, not a viewport BIM editor or IFC exporter. Five internal milestones produce one PR/ZIP.

V112–V266 adds project-scoped architecture image observation, roles for perspective/plan/elevation/section, image SHA256 and multiview verification groundwork. No trained ML checkpoint or semantic inference is bundled. Five milestones produce one PR and ZIP.

V117–V266 adds a rectangular schematic building shell parameterized by width/depth/floor height/level count, sharing canonical wall IDs between SVG plan/elevation and JSON geometry. This is an editable concept handoff, not image-inferred plans, technical MEP, full 3D renderer or certified IFC.

V122–V266 extends the same explicitly dimensioned rectangular BIM concept shell to front/rear/left/right elevations and two schematic sections. Diagrams do not infer rooms, roof construction, stairs, MEP or IFC, nor do they constitute a technical model.

V127–V266 exports a schematic plan as ASCII DXF (meter units, wall baseline LINE entities in level-specific layers), based on the same user-dimensioned canonical shell and SVG elevations/sections. DXF is editable 2D reference linework, not full architectural BIM, technical MEP or IFC. Five checkpoints produce one PR/ZIP.

V132–V266 adds a simple deterministic 55/45 two-zone conceptual floorplate based on user-entered size. Canonical space entities, shared wall partition and SVG drawing use the same dimensions; no AI room detection, opening placement, MEP or technical compliance is claimed.

V137–V266 validates conceptual room extents, partition alignment and floorplate area directly from the canonical BIM model. Windows CI now uses non-failing teardown after successful HTTP readiness. No technical architecture/MEP/IFC capability is inferred from the test.

V142–V266 includes an optional local CUDA Vision2Seq model inference interface. Users must supply a compatible model checkpoint; the CPU Windows Portable build does not contain trained architecture VLM weights and cannot execute CUDA inference without a suitable GPU/runtime. Descriptions are unverified AI suggestions and do not imply semantic BIM geometry, IFC, or technical compliance.

V147–V266 upgrades the existing VLM path to strict architecture observation JSON with visible evidence/uncertainty for building type, apparent floors, roof and facade. Inference failures and malformed model output are blocked. Only after explicit user confirmation of dimensions does the UI permit canonical schematic BIM handoff. Image inference does not determine metric dimensions or IFC-ready geometry. A real compatible locally provided CUDA model is needed; no checkpoint is bundled.

V152–V266 adds VLM cross-image evidence reconciliation. Upload up to 12 VLM JSON observations for one project to review consistent/contradictory building, apparent floor, roof and facade claims. Only actual completed locally run VLM records can be compared. Agreement does not prove metric dimensions, engineering compliance, or IFC-ready BIM.

V157–V266 upgrades the existing multiview VLM pipeline with an explicit design-approval gate before canonical concept BIM generation. The software rejects tampered consensus records and unresolved AI conflicts; it records per-image SHA256 fingerprints and the user-approved dimensions. No claim of photo-inferred metric dimensions, trained models bundled, technical MEP or IFC export.

V162–V266 extends evidence-gated multiview BIM approval with an advisory-only architectural review and reproducible verified checksum comparison. VLM observations never directly generate metric geometry: confirmed dimensions are mandatory. No trained checkpoint, image-to-BIM geometry synthesis, true IFC exporter or technical MEP is claimed.

Batch V167–V266 adds geometric wall mesh extrusion directly from canonical wall baselines and exports a real glTF binary (schematic_walls.glb) with a mapping file of canonical wall IDs. The geometric source is explicitly entered dimensions. The output remains a conceptual rectangular shell, not reconstructed from photography; no IFC, detailed spaces/MEP or engineering certification. GLB exporter uses trimesh and is tested for mesh reopening.

V172–V266 extends the canonical metric 3D building shell from walls to conceptual floor slabs on each level and exports named separate geometry nodes in the GLB. This is a schematic shell using user dimensions, not verified structural engineering or IFC. QA checks slab IDs/levels, non-mutating source and GLB roundtrip.

V177–V266 adds a pitched gable roof to the same canonical model as walls and slabs, exports separate ROOF_MAIN GLB geometry and ID mapping, and tests ridge height and GLB reopen. This is an open concept roof surface (not a watertight technical roof), dimensioned from user inputs rather than learned from photographs.

Batch V182–V266 deepens canonical 3D with actual hosted door/window wall voids. Door and window entities retain host IDs; GLB wall geometry is divided into solids around the void instead of transparent rectangles. Example openings are user-parametric, not derived from photos. The assembly remains concept geometry, without door leaves, complete detailed elevations, MEP or IFC.

V187–V266: GPU training is NOT enabled on the Windows CPU build runner. An explicitly configured and trusted Linux CUDA self-hosted runner labelled bimai360-gpu, Python 3.11 dependencies, licensed SD1.5 access and correctly staged private certified dataset/v72_certified are required to manually dispatch .github/workflows/gpu-train.yml. Run training only with permission for the data/model and a suitable GPU; no GPU inference/training runs have been verified on this PR. This trains an SD1.5 image LoRA, NOT an architecture VLM and NOT an image-to-BIM model. The independent canonical BIM category evaluation is only an evaluation scaffold and does not prove photo-to-BIM accuracy. No model weights are supplied or claimed trained.

V192–V266 fixes the GLB opening regression by validating the physical void, not exporter node names. VLM image inference now preflights local config, image processor and real safetensors filenames before attempting CUDA model loading. Preflight verifies presence/structure only: it does NOT certify model quality, real weights, completed inference or image-to-BIM model training. GPU runner and real architecture VLM weights are not included.

V197–V266 repairs prior regression to check actual GLB scene transforms rather than per-mesh local bounds. Adds strict independent-project holdout evaluation for observed VLM architectural properties including explicit unknown predictions and evaluation coverage. This evaluates supplied actual inference records; it does not infer architectural BIM or include VLM trained weights. GPU runner still required for training.

V202–V266 hardening: independent before/after exported GLB solid volume checks for the canonical door opening, instead of testing scene bounds that include slabs and roof. The JSONL VLM holdout evaluator reads actual recorded inference+labels and generates metrics; it is not itself training nor successful VLM inference. GPU runner and learned architecture checkpoint are not bundled.

V207–V266: architecture dataset ZIP/RAR audit and CUDA VRAM preflight are available. The user's NVIDIA T600 Laptop GPU requires VRAM measurement; the existing SD1.5 LoRA trainer requires >=8 GiB and a separately registered GitHub self-hosted CUDA runner. Uploaded private RARs have NOT yet been imported or certified in this release; do not claim the attached data is trained or bundled. See README_TRAIN_AND_DATASET.md. The image-to-BIM neural model and architecture VLM weights are not bundled.

V217–V266 workspace redesign: horizontal top tabs TẠO PHƯƠNG ÁN, KIỂM TRA, BÀN GIAO, DỮ LIỆU, ĐÀO TẠO, TÀI KHOẢN and contextual secondary tabs. One central export center browses only existing files inside output/. An offline local workspace can be opened without credentials and stores only display preferences, not passwords. This does not authenticate against a server; no passwords are embedded in the EXE. Activity logs are available in TÀI KHOẢN / Nhật ký.

V222–V266 deepens workflow in the first tab: check whether usable SD1.5 assets/GPU exist before generation, and produce an actual two-level canonical concept building (12m × 9m × 3.2m) with wall, slab, gable roof, hosted door/window, GLB, DXF, SVG and canonical JSON from one click in TẠO PHƯƠNG ÁN > Mô hình 2D/3D. This is a parametric sample, not image-to-BIM AI. This package does not include trained architecture VLM/LoRA model weights. Do not claim training. Layout remains workflow-oriented with a centralized export center.

V227–V266 improves output fidelity: black/blank generated images now fail before delivery with explicit diagnostic guidance, and generated gallery items reference actual PNGs saved on disk. New regression includes true Gradio Blocks configuration construction so UI tabs are verified beyond Python syntax. Actual end-user GPU inference, user-supplied photo file and trained architecture VLM remain unverified. Do not claim release PASS until Windows CI completes.

V232–V266: Vietnamese-only user-facing image role labels, explicit Vietnamese observation statuses and Vietnamese workflow terminology. Stable English protocol identifiers remain inside JSON/API payloads for interoperability. No pretrained architecture VLM or photo-to-full-BIM model checkpoint is bundled. Regression validates user display labels and API codes separately.

V237–V266 implements actual canonical building QA on every user-dimensioned handoff. Wall baselines, slab dimensions, floor levels, roof presence and opening hosts are checked against original dimensions, and KIEM_TRA_HINH_HOC.json is exported beside GLB/DXF/SVG/canonical JSON. Tampered or inconsistent model is rejected. This is conceptual geometry QA, NOT verified engineering design or photo-inferred BIM or IFC. Windows CI and EXE smoke remain required.

V242–V266 introduces full export/reopen roundtrip on real conceptual BIM package: read back canonical BIM JSON and compare checksum, load GLB triangles, compare wall/slab/roof IDs, parse plan/elevation SVG and verify structural DXF markers. Includes KIEM_TRA_MO_LAI.json file SHA256 report and blocks ZIP when output is corrupt, inconsistent or missing. This is not IFC or engineering verification. Windows EXE and CI still require PASS.

V247–V266 adds canonical-vs-GLB reopened geometric fidelity: expected volume from real wall segments and slab dimensions minus hosted opening volume; checks transformed GLB mesh solids, excluding open roof surfaces, within 0.005 m3. Fail closed if geometry differs; report embedded in KIEM_TRA_MO_LAI.json. This is conceptual validation only, not construction-approved BIM, IFC compliance or AI photo-to-BIM training.

V252–V266: edge reference actions are disabled until a real input image is uploaded; refresh/clear resets preview and download, errors become inline Vietnamese guidance rather than blocking popups. Default image generation quick preset is 1 output and 15 denoising steps for a faster first trial on limited VRAM. Actual model download, GPU offload and neural inference time remain hardware-dependent; no measured performance promise. Keeps V251 BIM/GLB volume fidelity checks.

V257–V266 fixes the real multiview BIM failure: enriched canonical models contain more than 4 entities per floor, so verify only the four required shell walls and matching levels rather than incorrectly counting slabs, roofs and hosted doors/windows as walls. Gaussian + median preprocessing reduces high-frequency noise in edge previews; 95 default threshold. Advanced CUDA-dependent image generation/upscale controls are disabled in sessions without CUDA; CPU-only image generation remains separate. No claim of trained architectural image-to-BIM. Release subject to CI and frozen EXE smoke.

V262–V266: image-generation button uses real nonempty editable English SD1.5 sample prompt rather than a misleading placeholder, catches backend model/checkpoint/GPU/VRAM/black-image failures, clears stale gallery/export on failure and shows safe Vietnamese diagnostic text in the status panel. This does not train a dedicated architectural image-to-BIM model. Existing V261 three-floor BIM and edge preview fixes are retained. Release needs full Windows CI PASS and EXE smoke.
