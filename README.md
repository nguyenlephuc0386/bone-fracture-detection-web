# 📖 Hướng Dẫn Chạy Website Nhận Dạng Gãy Xương

## Cấu Trúc Project

```
AG Test Code/
├── app.py                    # Server Flask (backend)
├── best.pt                   # Mô hình YOLO đã train
├── requirements.txt          # Danh sách thư viện cần cài
├── HUONG_DAN_CHAY.md         # File hướng dẫn này
├── templates/
│   └── index.html           # Giao diện website
├── static/
│   ├── css/
│   │   └── style.css        # Giao diện CSS
│   └── js/
│       └── main.js          # Logic JavaScript
├── uploads/                  # (tự tạo) Ảnh tải lên
├── results/                  # (tự tạo) Ảnh kết quả
└── fractures.db             # (tự tạo) Database SQLite
```

---

## Bước 1: Cài Đặt Python

**Yêu cầu**: Python 3.8 trở lên. Khuyến nghị Python 3.10 hoặc 3.11.

1. Tải Python tại: https://www.python.org/downloads/
2. Khi cài đặt, **nhớ tích vào "Add Python to PATH"**
3. Kiểm tra bằng cách mở **Command Prompt** (hoặc **PowerShell**) và gõ:
   ```
   python --version
   ```
   Nếu hiện `Python 3.x.x` là OK.

---

## Bước 2: Tạo Môi Trường Ảo (Khuyến Nghị)

Mở **Command Prompt** hoặc **PowerShell**, di chuyển vào thư mục project:

```bash
cd "d:\AG Test Code"
```

Tạo môi trường ảo:

```bash
python -m venv venv
```

Kích hoạt môi trường ảo:

- **Windows (Command Prompt)**:
  ```bash
  venv\Scripts\activate
  ```
- **Windows (PowerShell)**:
  ```bash
  venv\Scripts\Activate.ps1
  ```

Sau khi kích hoạt, bạn sẽ thấy `(venv)` xuất hiện đầu dòng lệnh.

---

## Bước 3: Cài Đặt Thư Viện

Chạy lệnh sau để cài tất cả thư viện cần thiết:

```bash
pip install -r requirements.txt
```

**Lưu ý**: Quá trình cài đặt có thể mất 5-10 phút do thư viện ultralytics và opencv-python khá lớn. Cần kết nối internet.

---

## Bước 4: Chạy Website

```bash
python app.py
```

Nếu chạy thành công, terminal sẽ hiện:

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

---

## Bước 5: Mở Website

Mở trình duyệt web (Chrome, Edge, Firefox...) và truy cập:

```
http://localhost:5000
```

---

## Cách Sử Dụng Website

### Nhận Diện Gãy Xương
1. Kéo thả ảnh X-quang vào khu vực upload, hoặc bấm "Chọn tệp từ máy tính"
2. Hỗ trợ định dạng: PNG và DICOM (.dcm)
3. Đợi hệ thống phân tích (thường mất 2-5 giây)
4. Xem kết quả: ảnh gốc vs ảnh đã nhận diện, thông tin chi tiết từng vùng gãy

### Tải Kết Quả
- Bấm "Tải PNG" để tải ảnh kết quả dạng PNG
- Bấm "Tải DICOM" để tải ảnh kết quả dạng DICOM (.dcm)

### Xem Lịch Sử
- Cuộn xuống mục "Lịch Sử Phân Tích" để xem các lần nhận diện trước
- Mỗi kết quả có nút Tải về (chọn PNG hoặc DICOM) và nút Xóa

### Liên Hệ
- Cuộn xuống mục "Liên Hệ & Hỗ Trợ" để xem thông tin bệnh viện và bác sĩ

---

## Xử Lý Lỗi Thường Gặp

- `ModuleNotFoundError`: Chưa cài thư viện -> Chạy `pip install -r requirements.txt`
- `FileNotFoundError: best.pt`: Đảm bảo file `best.pt` nằm cùng thư mục với `app.py`
- Port 5000 bị chiếm: Đổi port trong `app.py` (dòng cuối): `app.run(port=5001)`

---

## Tắt Website

Bấm **Ctrl + C** trong terminal để dừng server.

Tắt môi trường ảo:
```bash
deactivate
```
