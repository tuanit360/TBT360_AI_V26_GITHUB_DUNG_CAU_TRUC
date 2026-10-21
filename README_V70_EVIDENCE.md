# TBT360 AI V70 — Architecture/BIM Evidence Gate

V70 thêm kiểm tra **liên kết ảnh, bản vẽ, BIM JSON theo công trình**, xác nhận SHA256, kiểm tra cấu trúc BIM giới hạn, đánh giá checkpoint với các điểm số đo bên ngoài trên các công trình validation, và tạo đề xuất thay checkpoint yêu cầu người duyệt (có mã rollback).

Lệnh trên máy build/source (Python 3.11):

```bash
python -m tools.v70_evidence bundle --manifest PATH_TO_MANIFEST.json --root DATA_DIRECTORY --out report.json
python -m tools.v70_evidence trials --input measured_trials.json --out evaluation.json
python -m unittest discover -s tests -v
```

Manifest gồm `schema_version: tbt360-v70-project-evidence-v1`, `projects: [{project_id, assets:[{asset_id,kind,path,sha256,verification,canonical_asset_id?}]}]`. `kind` gồm `render`, `floorplan`, `elevation`, `section`, `bim_json`; mỗi ảnh/bản vẽ phải liên kết tới asset `bim_json`. SHA256 phải là hash của file thật. Không tự cấp trạng thái engineering_verified.

`measured_trials.json` là danh sách `{checkpoint, project_id, score}` với checkpoint nền tên `baseline`, cùng danh sách công trình validation, tối thiểu 2 công trình. Scores 0..1 phải là kết quả đo thực do quy trình đánh giá bên ngoài cung cấp; V70 **không tính ra chất lượng từ ảnh**, không huấn luyện trọng số, không tự deploy.

Báo cáo bundle chỉ kiểm tra ánh xạ, checksum và BIM JSON dạng footprint; không xác minh hình học tương ứng với pixel ảnh. Bộ kiểm thử có fixture giả lập để thử phát hiện lỗi, **không phải dữ liệu ảnh kiến trúc thực được huấn luyện**. Windows EXE/GPU chưa được build hoặc benchmark trong môi trường Linux này.
