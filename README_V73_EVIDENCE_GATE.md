# TBT360 AI V73 – Paired Architecture Geometry Evidence Gate

## Chức năng mới

- Đánh giá ảnh **đã được tạo trước đó** từ baseline/LoRA candidate theo cùng ảnh nguồn, prompt, negative prompt, seed và cấu hình.
- Yêu cầu mỗi ảnh có binary mask L (0 hoặc 255) do người đánh giá gán nhãn; mask tham chiếu phải là nguồn độc lập, không được giả là ground truth BIM nếu chưa được xác minh.
- Tính IoU mask cho từng ảnh, trung bình cho từng công trình holdout; mọi công trình validation phải xuất hiện, và ID train/validation không được trùng.
- SHA256 tất cả ảnh và mask; kiểm soát đường dẫn, độ phân giải, dữ liệu cặp ảnh, checksum checkpoint; kết quả chỉ là REVIEW_CANDIDATE (chờ duyệt) hoặc KEEP_BASELINE.
- Không tự thay trọng số, không tự huấn luyện, không tuyên bố kiểm chứng BIM theo mét hoặc thẩm định kỹ thuật.

## Chạy trên máy build

Chạy `DANH_GIA_V73_WINDOWS.bat` (khi đã có môi trường Python), hoặc:

`python -m evaluation.paired_gate reports/pairs_v73.json --assets dataset/heldout_evidence --output reports/v73_result.json`

Manifest mẫu **schema** (thay checksum bằng SHA256 thực của các file và checkpoint):

```json
{
  "schema_version": "tbt360-v73-paired-geometry-v1",
  "train_project_ids": ["office_train_01"],
  "validation_project_ids": ["office_holdout_01", "office_holdout_02"],
  "checkpoint_baseline_sha256": "<64 hex characters>",
  "checkpoint_candidate_sha256": "<64 hex characters>",
  "cases": [
    {
      "project_id": "office_holdout_01", "case_id": "front_daylight",
      "input_image": {"path": "input.png", "sha256": "<sha256>"},
      "reference_geometry_mask": {"path": "ref_mask.png", "sha256": "<sha256>"},
      "baseline": {
        "seed": 42, "prompt": "office front exterior", "negative_prompt": "",
        "settings": {"width": 1024, "height": 1024, "steps": 25, "cfg": 6},
        "input_sha256": "<sha256 of input.png>",
        "image": {"path": "baseline.png", "sha256": "<sha256>"},
        "geometry_mask": {"path": "baseline_mask.png", "sha256": "<sha256>"}
      },
      "candidate": {
        "seed": 42, "prompt": "office front exterior", "negative_prompt": "",
        "settings": {"width": 1024, "height": 1024, "steps": 25, "cfg": 6},
        "input_sha256": "<sha256 of input.png>",
        "image": {"path": "candidate.png", "sha256": "<sha256>"},
        "geometry_mask": {"path": "candidate_mask.png", "sha256": "<sha256>"}
      }
    }
  ]
}
```

Phải có trường hợp tương đương cho **mỗi** công trình trong validation; một case cho hai công trình không được coi là đủ. Kết quả ảnh cần sinh thực tế bằng pipeline trước khi chạy lệnh này. Cần chuyên gia kiểm tra chất lượng ảnh và độ trung thực hình học, vì IoU silhouette không đo chi tiết cửa, vật liệu, phối cảnh, đúng kích thước hay BIM.

## Giới hạn / trạng thái kiểm thử

Đã chạy unit tests bằng ảnh fixture **tổng hợp kiểm thử**, không phải ảnh kiến trúc thực hoặc kết quả GPU. Bản nguồn không kèm checkpoint lớn, model weights hay EXE Windows. Build Portable theo README_PORTABLE.md, chạy trên Windows và thử inference end-to-end trước khi triển khai.
