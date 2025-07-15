import cv2
import time
import logging
import threading
import numpy as np
from config import LICENSE_PLATE_CAMERA, PARKING_CAMERA

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraManager:
    # Khởi tạo camera
    def __init__(self, camera_type='license_plate'):
        self.camera_type = camera_type
        self.cap = None
        self.connected = False
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.last_frame_time = 0
        self.fps = 0
    
    # Kết nối đến camera
    def connect(self):
        if self.camera_type == 'license_plate':
            camera_config = LICENSE_PLATE_CAMERA
        else:
            camera_config = PARKING_CAMERA
        rtsp_url = camera_config['url'].format(
            username=camera_config['username'],
            password=camera_config['password'],
            ip=camera_config['ip'],
            port=camera_config['port']
        )
        try:
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(rtsp_url)
            if not self.cap.isOpened():
                logger.error(f"Không thể kết nối đến camera: {rtsp_url}")
                return None
            
            # Cài đặt độ phân giải và FPS
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Đọc một frame để kiểm tra
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Không thể đọc frame từ camera")
                return False
            logger.info(f"Đã kết nối thành công đến camera {self.camera_type}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Lỗi khi kết nối đến camera: {e}")
            self.connected = False
            return False
        
    # Bắt đầu đọc frame từ camera
    def start(self):
        if self.running:
            logger.warning("Camera đã được khởi động")
            return False
        if not self.connected:
            if not self.connect():
                logger.error("Không thể khởi động camera do kết nối thất bại")
                return False
        self.running = True
        
        # Tạo và khởi động thread
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        logger.info(f"Đã khởi động camera {self.camera_type}")
        return True
    
    # Dừng camera
    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.connected = False
        logger.info(f"Đã dừng camera {self.camera_type}")
    
    # Thread để đọc frame từ camera
    def _update_frame(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                logger.warning("Mất kết nối camera, đang thử kết nối lại...")
                self.connect()
                time.sleep(1)
                continue
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Không thể đọc frame từ camera")
                time.sleep(0.1)
                continue

            current_time = time.time()
            if self.last_frame_time != 0:
                self.fps = 1 / (current_time - self.last_frame_time)
            self.last_frame_time = current_time
            with self.lock:
                self.frame = frame.copy()
            time.sleep(0.01)
    
    # Lấy frame hiện tại từ camera
    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return np.zeros((720, 1280, 3), dtype=np.uint8)
            return self.frame.copy()
    
    # Lấy trạng thái camera
    def get_status(self):
        return {'connected': self.connected,'running': self.running,'fps': round(self.fps, 1)}


class GlobalCameraManager:
    """Singleton manager để quản lý tất cả camera trong ứng dụng"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(GlobalCameraManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.cameras = {}
        self._initialized = True
        logger.info("Đã khởi tạo GlobalCameraManager")
    
    def initialize_all_cameras(self):
        """Khởi tạo và kết nối tất cả camera khi khởi động ứng dụng"""
        try:
            # Khởi tạo camera biển số
            license_plate_camera = CameraManager('license_plate')
            if license_plate_camera.connect():
                license_plate_camera.start()
                self.cameras['license_plate'] = license_plate_camera
                logger.info("Đã khởi tạo camera biển số")
            else:
                logger.error("Không thể khởi tạo camera biển số")
            
            # Khởi tạo camera bãi đỗ xe
            parking_camera = CameraManager('parking')
            if parking_camera.connect():
                parking_camera.start()
                self.cameras['parking'] = parking_camera
                logger.info("Đã khởi tạo camera bãi đỗ xe")
            else:
                logger.error("Không thể khởi tạo camera bãi đỗ xe")
                
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo camera: {e}")
    
    def get_camera(self, camera_type):
        """Lấy camera theo loại"""
        return self.cameras.get(camera_type)
    
    def stop_all_cameras(self):
        """Dừng tất cả camera"""
        for camera in self.cameras.values():
            camera.stop()
        self.cameras.clear()
        logger.info("Đã dừng tất cả camera")


def get_camera_manager():
    """Hàm tiện ích để lấy instance của GlobalCameraManager"""
    return GlobalCameraManager()