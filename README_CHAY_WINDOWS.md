# TBT360 AI V26 — Deep Learning, giai đoạn 1

**Trạng thái thực tế:** Đây là workspace/source tạo ứng dụng Windows, KHÔNG chứa EXE đã build. Môi trường tạo gói hiện tại là Linux, không xác minh được EXE Windows. `BUILD_WINDOWS.bat` cần Python trong máy **chỉ cho người build**; máy người dùng cuối có thể chạy thư mục EXE do GitHub Actions xuất ra mà không cần Python. Không hứa chạy nếu Windows còn thiếu thư viện hệ thống hoặc driver tương thích.

## Hướng dẫn build Windows x64 tự động (không cần cài Python trên máy cá nhân)

1. Upload toàn bộ nội dung ZIP này lên một repository GitHub có quyền Actions; thư mục `.github/workflows` phải giữ nguyên. Chỉ dùng repo riêng tư nếu source/dữ liệu nhạy cảm. **Không cần upload dữ liệu ảnh để build**.
2. Vào **Actions → Windows native EXE build → Run workflow**. GitHub-hosted runner tải dependencies và build chương trình Windows thực bằng PyInstaller.
3. Sau khi workflow hiển thị thành công, tải artifact `TBT360_AI_WINDOWS_X64` từ workflow, giải nén đến thư mục bất kỳ.
4. Nhấp đôi `TBT360_AI.exe` bên trong `TBT360_AI/`. Không cần cài Python trên máy chạy. **Giữ nguyên các DLL/thư viện cạnh EXE**, không chỉ sao chép riêng EXE.
5. Nếu workflow lỗi, lấy log của Actions để điều chỉnh. Không tuyên bố PASS trước khi smoke-test trên Windows.

Tùy chọn: người xây dựng đã có Python 3.11 chạy `BUILD_WINDOWS.bat` trực tiếp trên Windows.

## Huấn luyện thử

Cần chuẩn bị thư mục **có nhãn đáng tin cậy**, ví dụ:

```
DU_LIEU_ANH/
  truong_hoc/
    001.jpg
    002.jpg
    003.jpg
  van_phong/
    001.jpg
    002.jpg
    003.jpg
```

Mỗi lớp tối thiểu 3 ảnh (khuyến nghị nhiều hơn, đa dạng, không trùng). Chạy ứng dụng → Chọn thư mục dữ liệu → BẮT ĐẦU HỌC SÂU → đợi hoàn tất. Mặc định dùng CPU vì máy NVIDIA T600 chưa được xác nhận tương thích CUDA/VRAM. Trong bản build mặc định, PyTorch có thể là bản CPU: chọn CUDA chỉ khi build có runtime CUDA phù hợp; nếu không, ứng dụng sẽ báo lỗi rõ.

Kết quả: `best.pt`, `last.pt`, `report.json`, `metrics.csv`. Biểu đồ hiển thị loss/accuracy từng epoch, màn hình báo tốc độ ảnh/giây. Có thể kiểm tra ảnh mới bằng nút tương ứng.

**Cảnh báo:** MobileNetV3 được huấn luyện từ đầu (không tự tải pretrained weights). Đây là deep learning thật, nhưng ảnh ít/trùng hoặc ảnh có nhãn sai sẽ khiến kết quả thiếu tin cậy. Chưa có calibration, external holdout hoặc chứng nhận accuracy. Không dùng xác suất thô làm độ tin cậy được hiệu chuẩn.

## Bộ dữ liệu ZIP/RAR đã nhận

Bản V26 **không tự giải nén/tự gán nhãn tất cả dữ liệu** vì ba gói ZIP trộn SVG, JSON, DXF, chỉ một phần là ảnh raster; hai RAR chưa được kiểm tra nhãn đầy đủ. `audit_archives.py` lập báo cáo metadata cho ZIP; SVG cần rasterize bằng công cụ được kiểm tra rồi ánh xạ nhãn thủ công từ manifest được xác minh. Không trộn ảnh chụp phối cảnh với mặt bằng 2D vào cùng nhãn theo suy đoán. Không dùng cùng mẫu công trình trong train và validation (cần split theo project_id khi triển khai bộ dữ liệu thật). Bản demo nhỏ hiện chỉ split theo ảnh và **không đủ để chứng minh khả năng tổng quát**.

## Giai đoạn 2 và 3 (CHƯA TRIỂN KHAI)

- Giai đoạn 2: đọc bản vẽ 2D: parser SVG/DXF và xác định hình học tường/cửa/phòng theo nhãn; cần bộ dữ liệu có ground truth, độ đo pixel/metre, đánh giá precision/recall và QA trực quan.
- Giai đoạn 3: BIM 3D: sinh/ánh xạ canonical entity (IDs/levels/host/units), dựng từ dữ liệu 2D được xác nhận, kiểm tra tính nhất quán 2D–3D và IFC round-trip; chưa có mô hình chuyển ảnh thành BIM đáng tin cậy.

## Phạm vi có thể xác minh

- Engine PyTorch huấn luyện MobileNetV3 từ đầu, cập nhật gradients thật.
- Có unit test tối thiểu: dataset split, 1 epoch, lưu và đọc model.
- Tkinter UI theo dõi epoch, loss, validation accuracy, tốc độ ảnh/giây, lỗi.
- Không có EXE thực trong ZIP này; build cần runner Windows với internet truy cập dependency. Build artifact có thể rất lớn (hàng trăm MB đến trên 1 GB). Dùng `--onedir` giúp kiểm tra DLL rõ hơn và giảm rủi ro khi chạy.
