ỨNG DỤNG CÔNG NGHỆ THÔNG MINH TRONG BÃI ĐỖ XE HIỆN ĐẠI

TÍNH NĂNG CHÍNH
    - Nhận diện biển số xe tự động - Sử dụng YOLOv5 + PaddleOCR
    - Giám sát bãi đỗ xe real-time - Phát hiện vị trí trống/đầy
    - Phát hiện vi phạm đỗ xe - Xe đậu sai vị trí, ra ngoài ranh giới
    - Quản lý thông tin sinh viên** - Liên kết biển số với MSSV
    - Thống kê và báo cáo - Biểu đồ theo ngày/tuần/tháng, xuất Excel

YÊU CẦU HỆ THỐNG
    - Python: 3.9 
    - GPU: NVIDIA GPU hoặc CPU
    - RAM: Tối thiểu 8GB
    - Camera: 2 camera IP hỗ trợ RTSP
    - Hệ điều hành: Windows 10/11, Linux

CÀI ĐẶT

1. Tải mã nguồn
    git clone https://github.com/your-username/smart-parking-system.git
    cd smart-parking-system

2. Tải models từ Google Drive
    Link tải models: https://drive.google.com/drive/folders/1Rbw7YWtw9gmFMujb_oAv_My8fNuvu4bm?usp=sharing

    Tải và giải nén folder `models` vào thư mục gốc của project:
    ```
    parking_system/
    ├── models/                     # ← Tải từ Google Drive
    │   ├── yolov5/
    │   ├── paddleocr/
    │   │   ├── ch_ppocr_mobile_v2.0_cls_infer
    │   │   ├── en_PP-OCRv3_rec_infer
    │   │   └── en_PP-OCRvD3_det_infer
    │   ├── CarParkPos
    │   └── LP_detector_nano_61.pt
    ├── main.py
    ├── config.py
    └── ...

 3. Cài đặt thư viện
    pip install -r requirements.txt

 4. Cấu hình camera trong file `config.py`
    # Cấu hình camera nhận diện biển số
    LICENSE_PLATE_CAMERA = {
        "username": "admin",
        "password": "your_password",
        "ip": "192.168.1.100",  # IP camera của bạn
        "port": "554",
        "url": "rtsp://{username}:{password}@{ip}:554/onvif1"
    }

    # Cấu hình camera bãi đỗ xe
    PARKING_CAMERA = {
        "username": "admin", 
        "password": "your_password",
        "ip": "192.168.1.101",  # IP camera của bạn
        "port": "554",
        "url": "rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1"
    }

CHẠY ỨNG DỤNG: python main.py
