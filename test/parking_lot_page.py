import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
import logging
import threading
import time
from datetime import datetime
from database.database_manager import DatabaseManager
from my_parking.camera import CameraManager, get_camera_manager
from my_parking.parking_spot import ParkingSpotDetector

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParkingLotPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.db_manager = DatabaseManager()
        camera_manager = get_camera_manager()
        self.camera = camera_manager.get_camera('parking')
        self.spot_detector = ParkingSpotDetector()
        self.running = False
        self.detection_thread = None
        self.stop_flag = threading.Event()
        self.marking_mode = False
        self.mouse_position = None
        self.setup_ui()
        logger.info("Đã khởi tạo trang quản lý bãi đỗ xe")
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Tiêu đề
        self.title_label = ctk.CTkLabel(
            self,
            text="Quản lý bãi đỗ xe",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Khung video
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.configure(width=1300, height=750)
        self.video_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.video_frame.grid_propagate(False)
        
        self.video_canvas = ctk.CTkCanvas(self.video_frame, bg="#1a1a1a", highlightthickness=0)
        self.video_canvas.pack(expand=True, fill="both")
        
        # Bind các sự kiện chuột
        self.video_canvas.bind("<Motion>", self.on_mouse_move)
        self.video_canvas.bind("<Button-1>", self.on_left_click)
        self.video_canvas.bind("<Button-3>", self.on_right_click)
        
        # Khung kết quả
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Số vị trí trống
        self.free_spots_frame = ctk.CTkFrame(self.result_frame)
        self.free_spots_frame.pack(fill="x", padx=20, pady=10)
        
        self.free_spots_title = ctk.CTkLabel(
            self.free_spots_frame,
            text="Số vị trí trống:",
            font=ctk.CTkFont(size=16)
        )
        self.free_spots_title.pack(side="left", padx=10)
        
        self.free_spots_value = ctk.CTkLabel(
            self.free_spots_frame,
            text="0 / 0",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4CAF50"
        )
        self.free_spots_value.pack(side="left", padx=10)
        
        # Danh sách vị trí trống
        self.available_spots_frame = ctk.CTkFrame(self.result_frame)
        self.available_spots_frame.pack(fill="x", padx=20, pady=10)
        
        self.available_spots_title = ctk.CTkLabel(
            self.available_spots_frame,
            text="Các vị trí trống:",
            font=ctk.CTkFont(size=16)
        )
        self.available_spots_title.pack(side="left", padx=10)
        
        self.available_spots_value = ctk.CTkLabel(
            self.available_spots_frame,
            text="---",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2196F3"
        )
        self.available_spots_value.pack(side="left", padx=10)
        
        # Nút điều khiển
        self.control_frame = ctk.CTkFrame(self.result_frame)
        self.control_frame.pack(fill="x", padx=20, pady=10)
        
        self.auto_detect_button = ctk.CTkButton(
            self.control_frame,
            text="Tự động phát hiện vạch vàng",
            font=ctk.CTkFont(size=14),
            command=self.auto_detect_yellow_lines
        )
        self.auto_detect_button.pack(side="left", padx=10, pady=10)
        
        self.marking_button = ctk.CTkButton(
            self.control_frame,
            text="Đánh dấu vị trí",
            font=ctk.CTkFont(size=14),
            command=self.toggle_marking_mode
        )
        self.marking_button.pack(side="left", padx=10, pady=10)
        
        self.clear_all_button = ctk.CTkButton(
            self.control_frame,
            text="Xóa tất cả vị trí",
            font=ctk.CTkFont(size=14),
            fg_color="#F44336",
            hover_color="#D32F2F",
            command=self.clear_all_positions
        )
        self.clear_all_button.pack(side="left", padx=10, pady=10)
    
    def on_enter(self):
        self.stop_flag.clear()
        self.running = True
        
        if self.camera is None:
            logger.error("Camera chưa được khởi tạo")
            return
        
        self.video_frame.configure(height=750, width=1300)
        
        # Load existing positions
        spot_count = self.spot_detector.get_spot_count()
        logger.info(f"DEBUG: Số lượng vị trí đã load từ file: {spot_count}")
        
        if spot_count > 0:
            self.sync_spots_to_database()
            logger.info(f"Đã tải {spot_count} vị trí đỗ xe từ file")
        else:
            logger.warning("Không có vị trí nào được load từ file!")
        
        self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.detection_thread.start()
        logger.info("Đã vào trang quản lý bãi đỗ xe")
    
    def on_leave(self):
        self.running = False
        self.stop_flag.set()
        
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
            self.detection_thread = None
        
        logger.info("Đã rời khỏi trang quản lý bãi đỗ xe")
    
    def detection_loop(self):
        frame_count = 0
        while self.running and not self.stop_flag.is_set():
            try:
                frame = self.camera.get_frame()
                if frame is None or frame.size == 0:
                    time.sleep(0.1)
                    continue
                
                frame_count += 1
                
                if self.marking_mode:
                    processed_frame = self.spot_detector.mark_position_mode(frame, self.mouse_position)
                else:
                    # Kiểm tra trạng thái các vị trí đỗ xe
                    processed_frame, spot_status, free_spots = self.spot_detector.check_parking_spaces(frame)
                    
                    # DEBUG
                    if frame_count % 30 == 0:
                        logger.info(f"DEBUG: Số vị trí detect: {len(spot_status)}, Free: {len(free_spots)}")
                        if len(spot_status) > 0:
                            logger.info(f"DEBUG: Spot status đầu tiên: {spot_status[0] if spot_status else 'None'}")
                    
                    self.update_spot_status(spot_status, free_spots)
                    self.update_database_spots(spot_status)
                
                processed_frame = self.add_status_to_frame(processed_frame)
                
                if processed_frame is None or processed_frame.size == 0:
                    time.sleep(0.1)
                    continue
                
                frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                h, w = frame_rgb.shape[:2]
                
                if h <= 0 or w <= 0:
                    time.sleep(0.1)
                    continue
                
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                video_w = self.video_canvas.winfo_width()
                video_h = self.video_canvas.winfo_height()
                
                if video_w > 0 and video_h > 0:
                    x_offset = max(0, (video_w - w) // 2)
                    y_offset = max(0, (video_h - h) // 2)
                    self.video_canvas.create_image(x_offset, y_offset, anchor="nw", image=imgtk)
                    self.video_canvas.image = imgtk
                else:
                    time.sleep(0.1)
                    continue
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp nhận diện: {e}")
                time.sleep(0.1)
    
    def auto_detect_yellow_lines(self):
        """
        Tự động phát hiện vạch vàng và tạo vị trí đỗ xe
        """
        try:
            frame = self.camera.get_frame()
            if frame is None:
                messagebox.showerror("Lỗi", "Không thể lấy hình ảnh từ camera!")
                return
            
            # Tự động phát hiện vạch vàng
            success = self.spot_detector.auto_initialize_spots(frame)
            
            if success:
                self.sync_spots_to_database()
                spot_count = self.spot_detector.get_spot_count()
                messagebox.showinfo(
                    "Thành công", 
                    f"Đã tự động phát hiện {spot_count} vị trí đỗ xe từ vạch vàng!"
                )
                logger.info(f"Đã tự động phát hiện {spot_count} vị trí đỗ xe")
            else:
                messagebox.showwarning(
                    "Cảnh báo", 
                    "Không phát hiện được vạch vàng nào!\nVui lòng kiểm tra ánh sáng và góc camera."
                )
                
        except Exception as e:
            logger.error(f"Lỗi khi tự động phát hiện vạch vàng: {e}")
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {e}")
    
    def update_spot_status(self, spot_status, free_spots):
        try:
            total_spots = len(spot_status)
            free_count = len(free_spots)
            
            self.free_spots_value.configure(text=f"{free_count} / {total_spots}")
            
            if free_spots:
                free_spots.sort()
                free_spots_text = ", ".join(free_spots)
            else:
                free_spots_text = "Không có vị trí trống"
            
            self.available_spots_value.configure(text=free_spots_text)
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trạng thái vị trí: {e}")
    
    def update_database_spots(self, spot_status):
        try:
            for spot in spot_status:
                spot_id = spot['spot_id']
                is_occupied = not spot['is_free']
                # Store additional size info if available
                position = spot.get('position', (0, 0))
                size = spot.get('size', (48, 107))
                self.db_manager.update_parking_spot(spot_id, is_occupied)
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cơ sở dữ liệu: {e}")
    
    def add_status_to_frame(self, frame):
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        status_frame = frame.copy()
        camera_status = self.camera.get_status()
        
        cv2.putText(
            status_frame,
            f"FPS: {camera_status['fps']}", 
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX,
            1, 
            (0, 255, 0), 
            2
        )
        
        return status_frame
    
    def clear_all_positions(self):
        result = messagebox.askyesno(
            title="Xác nhận xóa", 
            message="Bạn có chắc chắn muốn xóa tất cả vị trí đỗ xe không?\nHành động này không thể hoàn tác!"
        )
        
        if result:
            if self.spot_detector.clear_all_positions():
                self.sync_spots_to_database()
                messagebox.showinfo(
                    title="Thành công",
                    message="Đã xóa tất cả vị trí đỗ xe thành công!"
                )
                logger.info("Đã xóa tất cả vị trí đỗ xe thành công và cập nhật cơ sở dữ liệu")
            else:
                messagebox.showerror(
                    title="Lỗi", 
                    message="Có lỗi xảy ra khi xóa vị trí đỗ xe!"
                )
                logger.error("Lỗi khi xóa tất cả vị trí đỗ xe")
        else:
            logger.info("Người dùng đã hủy thao tác xóa tất cả vị trí")
    
    def sync_spots_to_database(self):
        try:
            conn = self.db_manager.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM parking_spots')
                conn.commit()
                conn.close()
            
            spot_count = self.spot_detector.get_spot_count()
            for i in range(spot_count):
                spot_id = f"A{i+1}"
                self.db_manager.update_parking_spot(spot_id, is_occupied=False)
            
            logger.info(f"Đã đồng bộ {spot_count} vị trí đỗ xe với cơ sở dữ liệu")
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ vị trí với cơ sở dữ liệu: {e}")
    
    def reconnect_camera(self):
        self.camera.stop()
        if self.camera.connect():
            self.camera.start()
            logger.info("Đã kết nối lại camera thành công")
        else:
            logger.error("Không thể kết nối lại camera")
    
    def on_mouse_move(self, event):
        if self.marking_mode:
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            frame_w, frame_h = 1280, 720
            
            x_offset = max(0, (canvas_w - frame_w) // 2)
            y_offset = max(0, (canvas_h - frame_h) // 2)
            
            real_x = event.x - x_offset
            real_y = event.y - y_offset
            
            if 0 <= real_x <= frame_w and 0 <= real_y <= frame_h:
                self.mouse_position = (real_x, real_y)
            else:
                self.mouse_position = None
    
    def on_left_click(self, event):
        if self.marking_mode:
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            frame_w, frame_h = 1280, 720
            
            x_offset = max(0, (canvas_w - frame_w) // 2)
            y_offset = max(0, (canvas_h - frame_h) // 2)
            
            real_x = event.x - x_offset
            real_y = event.y - y_offset
            
            if 0 <= real_x <= frame_w and 0 <= real_y <= frame_h:
                spot_data = {
                    'position': (real_x, real_y),
                    'size': (48, 107)  # Default size
                }
                self.spot_detector.add_position(spot_data)
                self.spot_detector.save_positions()
                self.sync_spots_to_database()
                logger.info(f"Đã thêm vị trí mới tại ({real_x}, {real_y})")
    
    def on_right_click(self, event):
        if self.marking_mode:
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            frame_w, frame_h = 1280, 720
            
            x_offset = max(0, (canvas_w - frame_w) // 2)
            y_offset = max(0, (canvas_h - frame_h) // 2)
            
            real_x = event.x - x_offset
            real_y = event.y - y_offset
            
            if self.spot_detector.remove_position((real_x, real_y)):
                self.spot_detector.save_positions()
                self.sync_spots_to_database()
                logger.info(f"Đã xóa vị trí gần ({real_x}, {real_y})")
    
    def toggle_marking_mode(self):
        self.marking_mode = not self.marking_mode
        if self.marking_mode:
            self.marking_button.configure(text="Tắt chế độ đánh dấu", fg_color="#F44336")
            logger.info("Đã bật chế độ đánh dấu vị trí")
        else:
            self.marking_button.configure(text="Đánh dấu vị trí", fg_color="#3a7ebf")
            logger.info("Đã tắt chế độ đánh dấu vị trí")