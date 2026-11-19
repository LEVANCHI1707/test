# Báo cáo chiến dịch Cốc Cốc Ads – Mộc Việt Home (dữ liệu mẫu)

Bộ báo cáo mẫu cho chiến dịch quảng cáo "Tổ ấm mùa thu" (T5–T10/2026) của một khách hàng giả định trên Cốc Cốc. **Toàn bộ số liệu là dữ liệu mẫu để minh hoạ.**

| File | Nội dung |
|---|---|
| `mocviet_coccoc_campaign.csv` | Dữ liệu theo tháng × định dạng quảng cáo (hiển thị, click, chi phí, chuyển đổi, doanh thu) |
| `mocviet_coccoc_report.html` | Trang báo cáo: chỉ số tổng quan, biểu đồ cột, bảng chi tiết. Mở trực tiếp bằng trình duyệt; có nút nạp CSV khác, đổi sáng/tối, in PDF |
| `mocviet_coccoc_video.mp4` | Video trình chiếu ~1 phút 52 giây, giọng đọc nữ (Microsoft HoaiMy) và phụ đề tiếng Việt |
| `mocviet_coccoc_video.srt` | Phụ đề dạng file riêng |
| `make_video.py` | Script dựng lại video từ file CSV |

## Dựng lại video

Cần Python 3.10+ và FFmpeg:

```powershell
winget install Gyan.FFmpeg
pip install edge-tts pillow
python make_video.py
```

Lời đọc và phụ đề nằm trong danh sách `SCENES` của `make_video.py`. Script dùng font Segoe UI của Windows.
