# Cấu hình cơ sở dữ liệu
DB_PATH = 'database/parking_system.db'

# Cấu hình camera nhận diện biển số xe
LICENSE_PLATE_CAMERA = {
    "username": "admin",
    "password": "admin123",
    "ip": "192.168.137.106",
    "port": "554",
    "url": "rtsp://{username}:{password}@{ip}:554/onvif1"
}

# Cấu hình camera bãi đỗ xe
PARKING_CAMERA = {
    "username": "admin",
    "password": "L250C321",
    "ip": "192.168.142.201",
    "port": "554",
    "url": "rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1"
}

# Cấu hình đường dẫn mô hình
MODEL_PATHS = {
    'yolov5_path': './models/yolov5',
    'license_plate_model': './models/LP_detector_nano_61.pt',
    'parking_space_model': './models/PK_detector_v5m.pt',
    'paddle_det_model': './models/paddleocr/en_PP-OCRvD3_det_infer',
    'paddle_rec_model': './models/paddleocr/en_PP-OCRv3_rec_infer',
    'paddle_cls_model': './models/paddleocr/ch_ppocr_mobile_v2.0_cls_infer',
    'parking_positions': './models/CarParkPos'
}

# Cấu hình giao diện
UI_CONFIG = {
    'title': 'Hệ thống bãi giữ xe sinh viên',
    'width': 1200,
    'height': 800,
    'theme': 'dark-blue'  
}

# Cấu hình thời gian làm mới dữ liệu (ms)
REFRESH_RATES = {
    'camera': 10,            
    'statistics': 60000,     
    'database': 5000         
}