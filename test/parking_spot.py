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
        self.spot_width = 96
        self.spot_height = 250
        self.occupancy_threshold = 0.6  # 60% pixel threshold for occupancy
        self.load_positions()
    
    def detect_yellow_lines(self, frame):
        """
        Tự động phát hiện vạch vàng và tạo vị trí đỗ xe với nhiều dải màu vàng
        """
        try:
            # Chuyển sang HSV để phát hiện màu vàng tốt hơn
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Định nghĩa nhiều dải màu vàng cho băng keo (mở rộng cho ánh sáng thực tế)
            yellow_ranges = [
                # ([8, 50, 50], [45, 255, 255]),     # Rất rộng cho ánh sáng thay đổi
                # ([5, 40, 40], [50, 255, 255]),     # Vàng nhạt trong bóng
                ([10, 60, 80], [40, 255, 255]),    # Vàng sáng
                # ([0, 30, 80], [35, 255, 255]),     # Vàng cam
                # ([15, 100, 100], [35, 255, 200])   # Vàng đậm
            ]
            
            # Tạo mask tổng hợp
            combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            
            for lower, upper in yellow_ranges:
                lower_yellow = np.array(lower)
                upper_yellow = np.array(upper)
                mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            # Làm sạch noise mạnh hơn cho băng keo
            kernel = np.ones((3, 3), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # Tìm contours của vạch vàng
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            parking_spots = []
            
            for contour in contours:
                # Lọc contours theo diện tích (giảm threshold nhiều cho băng keo nhỏ)
                area = cv2.contourArea(contour)
                if area > 500:  # Giảm từ 800 xuống 500
                    # Tính bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Kiểm tra tỷ lệ khung hình và kích thước tối thiểu
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # Mở rộng điều kiện cho hình chữ nhật dài
                    if 0.5 < aspect_ratio < 8.0 and w > 20 and h > 15:
                        # Vẽ khung phát hiện màu vàng (màu cyan)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
                        cv2.putText(frame, f"Yellow {len(parking_spots)+1}", (x, y-5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        
                        # Tính vị trí trung tâm để đặt khung 48x107
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        # Đặt khung 48x107 ở trung tâm
                        spot_x = center_x - self.spot_width // 2
                        spot_y = center_y - self.spot_height // 2
                        
                        # Vẽ khung đỗ xe 48x107 (màu đỏ)
                        cv2.rectangle(frame, (spot_x, spot_y), (spot_x + self.spot_width, spot_y + self.spot_height), (0, 0, 255), 2)
                        cv2.putText(frame, f"Spot {len(parking_spots)+1}", (spot_x, spot_y-5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        
                        # Lưu vị trí đỗ xe
                        parking_spots.append({
                            'position': (spot_x, spot_y),
                            'size': (self.spot_width, self.spot_height)
                        })
                        logger.info(f"Phát hiện vùng vàng: vị trí=({x},{y}), kích thước=({w},{h}), spot=({spot_x},{spot_y})")
            
            logger.info(f"Tổng số vùng vàng phát hiện: {len(parking_spots)}")
            return parking_spots
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện vạch vàng: {e}")
            return []
    
    def debug_yellow_detection(self, frame):
        """
        Debug function để hiển thị mask và điều chỉnh dải màu
        """
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Test với nhiều dải màu
            yellow_ranges = [
                # ([15, 80, 80], [35, 255, 255]),
                # ([10, 50, 50], [40, 255, 255]),
                ([20, 100, 100], [30, 255, 255]),
                # ([18, 60, 120], [32, 255, 255]),
                # ([12, 40, 80], [38, 255, 200])
            ]
            
            debug_frame = frame.copy()
            
            for i, (lower, upper) in enumerate(yellow_ranges):
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                
                # Vẽ kết quả từng mask
                colored_mask = cv2.applyColorMap(mask, cv2.COLORMAP_JET)
                debug_frame = cv2.addWeighted(debug_frame, 0.7, colored_mask, 0.3, 0)
                
                # In thông tin
                cv2.putText(debug_frame, f"Range {i+1}", (10, 30 + i*25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return debug_frame
            
        except Exception as e:
            logger.error(f"Lỗi debug: {e}")
            return frame
    def auto_initialize_spots(self, frame):
        """
        Tự động khởi tạo vị trí đỗ xe từ vạch vàng
        """
        try:
            detected_spots = self.detect_yellow_lines(frame)
            
            if detected_spots:
                # Lưu cả vị trí và kích thước
                self.posList = detected_spots
                self.save_positions()
                logger.info(f"Đã tự động phát hiện {len(detected_spots)} vị trí đỗ xe từ vạch vàng")
                return True
            else:
                logger.warning("Không phát hiện được vạch vàng nào")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi tự động khởi tạo vị trí: {e}")
            return False
    
    def calculate_occupancy_by_pixels(self, frame, spot_data):
        """
        Tính toán độ lấp đầy dựa trên số lượng pixel với kích thước thực tế
        """
        try:
            if isinstance(spot_data, dict):
                x, y = spot_data['position']
                w, h = spot_data['size']
            else:
                # Backward compatibility với format cũ
                x, y = spot_data
                w, h = self.spot_width, self.spot_height
            
            # Trích xuất vùng đỗ xe với kích thước thực tế
            roi = frame[y:y+h, x:x+w]
            
            if roi.size == 0:
                return False
            
            # Chuyển sang grayscale
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Áp dụng threshold để phân biệt foreground/background
            _, binary = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Đếm pixel foreground (có thể là xe)
            foreground_pixels = cv2.countNonZero(binary)
            total_pixels = roi.shape[0] * roi.shape[1]
            
            # Tính tỷ lệ lấp đầy
            occupancy_ratio = foreground_pixels / total_pixels
            
            # Quyết định có xe hay không dựa trên threshold
            is_occupied = occupancy_ratio > self.occupancy_threshold
            
            return is_occupied
            
        except Exception as e:
            logger.error(f"Lỗi khi tính toán độ lấp đầy: {e}")
            return False
    
    def check_parking_spaces(self, frame):
        """
        Kiểm tra trạng thái các vị trí đỗ xe sử dụng pixel counting với kích thước cố định
        """
        logger.debug(f"DEBUG: check_parking_spaces được gọi với {len(self.posList)} vị trí")
        
        if len(self.posList) == 0:
            logger.debug("DEBUG: Không có vị trí nào để kiểm tra!")
            return frame, [], []
            
        try:
            spaces_status = []
            free_spaces = []
            
            logger.debug(f"DEBUG: Bắt đầu xử lý {len(self.posList)} vị trí")
            
            for i, spot_data in enumerate(self.posList):
                # Xử lý cả format mới (dict) và cũ (tuple)
                if isinstance(spot_data, dict):
                    x, y = spot_data['position']
                else:
                    # Backward compatibility
                    x, y = spot_data
                
                # Sử dụng phương pháp đếm pixel với kích thước cố định
                roi_data = {'position': (x, y), 'size': (self.spot_width, self.spot_height)}
                is_occupied = self.calculate_occupancy_by_pixels(frame, roi_data)
                is_free = not is_occupied
                
                # Vẽ khung với kích thước cố định như mouse click
                color = (0, 255, 0) if is_free else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + self.spot_width, y + self.spot_height), color, 2)
                
                spot_id = f"A{i+1}"
                cv2.putText(frame, spot_id, (x, y + self.spot_height - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                status = {
                    'spot_id': spot_id, 
                    'is_free': is_free, 
                    'position': (x, y),
                    'size': (self.spot_width, self.spot_height)
                }
                spaces_status.append(status)
                
                if is_free:
                    free_spaces.append(spot_id)
                    
                # DEBUG cho vị trí đầu tiên
                if i == 0:
                    logger.debug(f"DEBUG: Vị trí đầu tiên - Pos: ({x},{y}), Size: ({self.spot_width},{self.spot_height}), Color: {color}, Is_free: {is_free}")
            
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
        self.posList.append(spot_data)
        logger.info(f"DEBUG: Đã thêm vị trí đỗ xe. Tổng: {len(self.posList)}")
    
    def remove_position(self, position, threshold=30):
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
        logger.debug(f"DEBUG: mark_position_mode được gọi với {len(self.posList)} vị trí")
        
        for i, spot_data in enumerate(self.posList):
            if isinstance(spot_data, dict):
                x, y = spot_data['position']
            else:
                x, y = spot_data
            
            # Vẽ với kích thước cố định giống mouse click
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