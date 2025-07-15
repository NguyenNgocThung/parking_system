import cv2
import pickle
import numpy as np
import logging
import os
from config import MODEL_PATHS, PARKING_CAMERA

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParkingSpotDetector:
    def __init__(self):
        self.posList = []
        self.spot_width = 150
        self.spot_height = 400
        self.occupancy_threshold = 0.3  # Threshold để phát hiện xe
        self.violation_buffer = 20  # Buffer zone để kiểm tra vi phạm (pixels)
        self.load_positions()
    
    def check_vehicle_in_spot_boundary(self, frame, spot_data):
        """
        Kiểm tra xe có đậu đúng trong ranh giới ô đỗ hay không - SỬA LỖI
        """
        try:
            if isinstance(spot_data, dict):
                x, y = spot_data['position']
                w, h = spot_data['size']
            else:
                x, y = spot_data
                w, h = self.spot_width, self.spot_height
            
            # BƯỚC 1: Kiểm tra có xe trong ô không (như cũ)
            roi = frame[y:y+h, x:x+w]
            if roi.size == 0:
                return False, False
            
            # Phát hiện xe trong ô chính
            vehicle_in_spot_pixels = self.count_vehicle_pixels_in_area(roi)
            
            # NGƯỠNG: Có xe nếu > 1000 pixels
            has_vehicle_in_spot = vehicle_in_spot_pixels > 1000
            
            # BƯỚC 2: Chỉ kiểm tra vi phạm khi CÓ XE trong ô
            is_violation = False
            
            if has_vehicle_in_spot:
                # Mở rộng vùng để kiểm tra xe có lệch ra ngoài không
                buffer = 20
                expand_x = max(0, x - buffer)
                expand_y = max(0, y - buffer)
                expand_w = min(frame.shape[1] - expand_x, w + 2*buffer)
                expand_h = min(frame.shape[0] - expand_y, h + 2*buffer)
                
                expanded_roi = frame[expand_y:expand_y+expand_h, expand_x:expand_x+expand_w]
                
                # Đếm xe trong vùng mở rộng
                total_vehicle_pixels = self.count_vehicle_pixels_in_area(expanded_roi)
                
                # Xe ngoài ô = tổng xe - xe trong ô
                vehicle_outside_pixels = total_vehicle_pixels - vehicle_in_spot_pixels
                
                # VI PHẠM nếu có nhiều xe ngoài ô (> 50% xe trong ô)
                if vehicle_outside_pixels > vehicle_in_spot_pixels * 0.5:
                    is_violation = True
                    logger.debug(f"Vi phạm: xe trong ô={vehicle_in_spot_pixels}, xe ngoài ô={vehicle_outside_pixels}")
            
            return has_vehicle_in_spot, is_violation
            
        except Exception as e:
            logger.error(f"Lỗi kiểm tra ranh giới: {e}")
            return False, False
    
    def count_vehicle_pixels_in_area(self, roi):
        """
        Đếm số pixels xe trong một vùng
        """
        try:
            if roi.size == 0:
                return 0
            
            # Chuyển sang HSV và grayscale
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Phát hiện vật thể tối (xe máy)
            lower_dark = np.array([0, 0, 0])
            upper_dark = np.array([179, 255, 120])
            dark_mask = cv2.inRange(hsv_roi, lower_dark, upper_dark)
            
            # Adaptive threshold
            adaptive_mask = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                cv2.THRESH_BINARY_INV, 15, 5)
            
            # Kết hợp
            combined_mask = cv2.bitwise_or(dark_mask, adaptive_mask)
            
            # Làm sạch noise
            kernel = np.ones((3, 3), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # Loại bỏ vùng nhỏ
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            filtered_mask = np.zeros_like(combined_mask)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 200:  # Giảm threshold để nhạy hơn
                    cv2.fillPoly(filtered_mask, [contour], 255)
            
            # Đếm pixels xe
            vehicle_pixels = cv2.countNonZero(filtered_mask)
            return vehicle_pixels
            
        except Exception as e:
            logger.error(f"Lỗi đếm pixels xe: {e}")
            return 0
    
    def check_parking_spaces(self, frame):
        """
        Kiểm tra trạng thái các vị trí đỗ xe - với kiểm tra vi phạm ranh giới
        """
        logger.debug(f"DEBUG: check_parking_spaces được gọi với {len(self.posList)} vị trí")
        
        if len(self.posList) == 0:
            logger.debug("DEBUG: Không có vị trí nào để kiểm tra!")
            return frame, [], []
            
        try:
            spaces_status = []
            free_spaces = []
            
            logger.debug(f"DEBUG: Bắt đầu xử lý {len(self.posList)} vị trí")
            
            # Kiểm tra từng vị trí đỗ xe
            for i, spot_data in enumerate(self.posList):
                if isinstance(spot_data, dict):
                    x, y = spot_data['position']
                else:
                    x, y = spot_data
                
                # Kiểm tra xe có trong ô và có vi phạm không
                has_vehicle, is_violation = self.check_vehicle_in_spot_boundary(frame, spot_data)
                
                is_free = not has_vehicle
                is_occupied = has_vehicle
                
                # Xác định màu hiển thị
                if is_free:
                    color = (0, 255, 0)  # Green - empty
                elif is_violation:
                    color = (0, 165, 255)  # Orange - violation (xe đỗ lệch)
                else:
                    color = (0, 0, 255)  # Red - occupied properly
                
                # Vẽ khung với màu tương ứng
                cv2.rectangle(frame, (x, y), (x + self.spot_width, y + self.spot_height), color, 2)
                
                # Hiển thị ID
                spot_id = f"A{i+1}"
                cv2.putText(frame, spot_id, (x, y + self.spot_height - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Hiển thị text vi phạm nếu có
                if is_violation:
                    cv2.putText(frame, "DO SAI", (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                
                status = {
                    'spot_id': spot_id, 
                    'is_free': is_free, 
                    'is_occupied': is_occupied,
                    'is_violation': is_violation,
                    'position': (x, y),
                    'size': (self.spot_width, self.spot_height)
                }
                spaces_status.append(status)
                
                if is_free:
                    free_spaces.append(spot_id)
            
            logger.debug(f"DEBUG: Đã xử lý xong. Status: {len(spaces_status)}, Free: {len(free_spaces)}")
            return frame, spaces_status, free_spaces
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vị trí đỗ xe: {e}")
            return frame, [], []
    
    def load_positions(self):
        """
        Tải vị trí các ô đỗ xe từ file
        """
        file_path = MODEL_PATHS['parking_positions']
        logger.info(f"DEBUG: Đang tải vị trí từ file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"DEBUG: File không tồn tại: {file_path}")
            logger.info("Tạo file vị trí đỗ xe mới...")
            self.posList = []
            self.create_new_positions_file()
            return
        
        file_size = os.path.getsize(file_path)
        logger.info(f"DEBUG: Kích thước file: {file_size} bytes")
        
        if file_size == 0:
            logger.warning(f"DEBUG: File trống: {file_path}")
            self.posList = []
            self.create_new_positions_file()
            return
            
        try:
            with open(file_path, 'rb') as f:
                self.posList = pickle.load(f)
            logger.info(f"DEBUG: Đã tải thành công {len(self.posList)} vị trí đỗ xe")
            
            for i, pos in enumerate(self.posList):
                logger.info(f"DEBUG: Vị trí {i+1}: {pos}")
                
        except FileNotFoundError:
            logger.warning(f"Không tìm thấy file vị trí đỗ xe: {file_path}")
            logger.info("Tạo file vị trí đỗ xe mới...")
            self.posList = []
            self.create_new_positions_file()
        except Exception as e:
            logger.error(f"Lỗi khi tải vị trí đỗ xe: {e}")
            logger.info("Tạo file vị trí đỗ xe mới do lỗi...")
            self.posList = []
            self.create_new_positions_file()
    
    def save_positions(self):
        """
        Lưu vị trí các ô đỗ xe vào file
        """
        try:
            positions_dir = os.path.dirname(MODEL_PATHS['parking_positions'])
            if positions_dir:
                os.makedirs(positions_dir, exist_ok=True)
            
            with open(MODEL_PATHS['parking_positions'], 'wb') as f:
                pickle.dump(self.posList, f)
            logger.info(f"Đã lưu {len(self.posList)} vị trí đỗ xe")
            
            file_size = os.path.getsize(MODEL_PATHS['parking_positions'])
            logger.info(f"DEBUG: File size sau khi lưu: {file_size} bytes")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu vị trí đỗ xe: {e}")
    
    def create_new_positions_file(self):
        """
        Tạo file vị trí đỗ xe mới
        """
        try:
            positions_dir = os.path.dirname(MODEL_PATHS['parking_positions'])
            if positions_dir and not os.path.exists(positions_dir):
                os.makedirs(positions_dir, exist_ok=True)
                logger.info(f"Đã tạo thư mục: {positions_dir}")
            
            with open(MODEL_PATHS['parking_positions'], 'wb') as f:
                pickle.dump(self.posList, f)
            logger.info(f"Đã tạo file vị trí đỗ xe mới: {MODEL_PATHS['parking_positions']}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo file vị trí đỗ xe mới: {e}")
    
    def clear_all_positions(self):
        """
        Xóa toàn bộ vị trí đỗ xe và tạo file mới
        """
        try:
            logger.info(f"DEBUG: Xóa {len(self.posList)} vị trí")
            self.posList = []
            self.save_positions()
            logger.info("Đã xóa toàn bộ vị trí đỗ xe")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa toàn bộ vị trí: {e}")
            return False
    
    def get_spot_count(self):
        """
        Trả về số lượng ô đỗ xe
        """
        count = len(self.posList)
        logger.debug(f"DEBUG: get_spot_count trả về: {count}")
        return count
    
    def add_position(self, spot_data):
        """
        Thêm vị trí đỗ xe mới
        """
        self.posList.append(spot_data)
        logger.info(f"DEBUG: Đã thêm vị trí đỗ xe. Tổng: {len(self.posList)}")
    
    def remove_position(self, position, threshold=30):
        """
        Xóa vị trí đỗ xe gần nhất
        """
        for i, spot_data in enumerate(self.posList):
            if isinstance(spot_data, dict):
                x1, y1 = spot_data['position']
            else:
                x1, y1 = spot_data
            
            x2, y2 = position
            distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if distance < threshold:
                removed_spot = self.posList.pop(i)
                logger.info(f"DEBUG: Đã xóa vị trí đỗ xe. Còn lại: {len(self.posList)}")
                return True
        return False
    
    def mark_position_mode(self, frame, mousepos=None):
        """
        Chế độ đánh dấu vị trí thủ công
        """
        logger.debug(f"DEBUG: mark_position_mode được gọi với {len(self.posList)} vị trí")
        
        for i, spot_data in enumerate(self.posList):
            if isinstance(spot_data, dict):
                x, y = spot_data['position']
            else:
                x, y = spot_data
            
            # Vẽ với kích thước cố định
            cv2.rectangle(frame, (x, y), (x + self.spot_width, y + self.spot_height), (0, 255, 0), 2)
                
        if mousepos:
            x, y = mousepos
            cv2.rectangle(frame, (x, y), (x + self.spot_width, y + self.spot_height), (255, 0, 0), 2)
        
        return frame

def connect_to_parking_camera():
    """
    Kết nối đến camera bãi đỗ xe
    """
    rtsp_url = PARKING_CAMERA['url']
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        logger.error(f"Không thể kết nối đến camera bãi đỗ xe: {rtsp_url}")
        return None
    logger.info("Đã kết nối thành công đến camera bãi đỗ xe")
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    return cap