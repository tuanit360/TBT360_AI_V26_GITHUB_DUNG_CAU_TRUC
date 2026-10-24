"""Vietnamese labels with stable English protocol identifiers for BIMAI360."""
IMAGE_ROLES = {
    'Ảnh phối cảnh ngoại thất': 'exterior_perspective',
    'Ảnh nội thất': 'interior',
    'Bản vẽ mặt bằng': 'floorplan',
    'Bản vẽ mặt đứng': 'elevation',
    'Bản vẽ mặt cắt': 'section',
}
STATUS_LABELS = {
    'unknown': 'Chưa có thông tin',
    'conflict': 'Có mâu thuẫn, cần kiểm tra',
    'unverified_agreement': 'Các ảnh cho cùng nhận định (chưa xác minh)',
    'started': 'Đang thực hiện',
    'completed': 'Hoàn thành',
    'failed': 'Thất bại',
}
def image_role_code(label):
    if label not in IMAGE_ROLES:
        raise ValueError('Loại ảnh không hợp lệ')
    return IMAGE_ROLES[label]


def translate_report(data):
    """Present a Vietnamese explanation while preserving machine keys."""
    if not isinstance(data, dict):
        return {'thong_bao': 'Không có báo cáo hợp lệ'}
    status = data.get('verification_status') or data.get('status')
    return {
        'trang_thai': STATUS_LABELS.get(status, 'Chưa xác minh'),
        'ma_cong_trinh': data.get('project_id'),
        'da_chay_suy_luan_ai': bool(data.get('model_inference_performed', False)),
        'anh_da_tiep_nhan': bool(data.get('image_pixels_sha256')),
        'ghi_chu': 'Dữ liệu ảnh đã ghi nhận; chưa chứng minh AI đã dựng BIM đầy đủ.',
        'du_lieu_ky_thuat': data,
    }
