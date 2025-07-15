import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
import logging
import threading
import time
from datetime import datetime
from database.database_manager import DatabaseManager
from my_parking.camera import CameraManager
from my_parking.license_plate import LicensePlateDetector
from my_parking.camera import get_camera_manager

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VehicleInOutPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.db_manager = DatabaseManager()
        camera_manager = get_camera_manager()
        self.camera = camera_manager.get_camera('license_plate')
        self.plate_detector = LicensePlateDetector()
        self.running = False
        self.processing = False
        self.detection_thread = None
        self.stop_flag = threading.Event()
        self.cooldown_time = 10.0  # 5 giây
        self.last_detection_time = 0
        self.last_detected_plate = None
        self.setup_ui()    
        logger.info("Đã khởi tạo trang quản lý xe vào/ra")
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.title_label = ctk.CTkLabel(self, text="Quản lý xe vào/ra",font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.video_frame.grid_propagate(False)  
        self.video_label = tk.Label(self.video_frame, bg="#1a1a1a")
        self.video_label.pack(expand=True, fill="both")
        # Khung kết quả
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        # Kết quả nhận diện
        self.result_label_frame = ctk.CTkFrame(self.result_frame)
        self.result_label_frame.pack(fill="x", padx=20, pady=10)
        self.result_title = ctk.CTkLabel(self.result_label_frame,text="Kết quả nhận diện biển số:",font=ctk.CTkFont(size=16))
        self.result_title.pack(side="left", padx=10)
        self.result_value = ctk.CTkLabel(self.result_label_frame,text="---",font=ctk.CTkFont(size=16, weight="bold"),text_color="#4CAF50")
        self.result_value.pack(side="left", padx=10)
        # Trạng thái xe vào/ra
        self.inout_frame = ctk.CTkFrame(self.result_frame)
        self.inout_frame.pack(fill="x", padx=20, pady=10)
        self.inout_title = ctk.CTkLabel(self.inout_frame,text="Trạng thái:",font=ctk.CTkFont(size=16))
        self.inout_title.pack(side="left", padx=10)
        self.inout_value = ctk.CTkLabel(self.inout_frame,text="---",font=ctk.CTkFont(size=16, weight="bold"),text_color="#2196F3")
        self.inout_value.pack(side="left", padx=10)
        # Khung log hoạt động
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.log_title = ctk.CTkLabel(self.log_frame,text="Log hoạt động",font=ctk.CTkFont(size=16, weight="bold"))
        self.log_title.pack(anchor="w", padx=10, pady=(10, 5))
        self.log_text = ctk.CTkTextbox(self.log_frame,height=100,font=ctk.CTkFont(size=12))
        self.log_text.pack(fill="x", padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")
    
    def on_enter(self):
        self.stop_flag.clear()
        self.running = True
        self.video_frame.configure(height=480, width=640)
        self.video_label.configure(width=640, height=480)
        self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.detection_thread.start()
        self.add_log_message("Đã khởi động hệ thống nhận diện biển số.")
        logger.info("Đã vào trang quản lý xe vào/ra")
    
    def on_leave(self):
        self.running = False
        self.stop_flag.set()
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
            self.detection_thread = None
        self.add_log_message("Đã dừng hệ thống nhận diện biển số.")
        logger.info("Đã rời khỏi trang quản lý xe vào/ra")
    
    def detection_loop(self):
        while self.running and not self.stop_flag.is_set():
            try:
                frame = self.camera.get_frame()
                if frame is None or frame.size == 0:
                    time.sleep(0.1)
                    continue
                height, width = frame.shape[:2]
                frame = frame[height//2:height, 0:width]  # Bottom half only
                frame = frame[60:, :]  # Crop top 30 pixels
                current_time = time.time()
                can_process = current_time - self.last_detection_time > self.cooldown_time
                if can_process and not self.processing:
                    plates = self.plate_detector.detect_license_plates(frame.copy())
                    if plates:
                        self.processing = True
                        processing_thread = threading.Thread(target=self.process_detected_plates,args=(plates,),daemon=True)
                        processing_thread.start()
                
                # Vẽ khung biển số nếu có (không cần OCR để vẽ khung)
                display_plates = self.plate_detector.detect_license_plates(frame.copy())
                if display_plates:
                    frame = self.plate_detector.annotate_frame(frame, display_plates)
                frame = self.add_status_to_frame(frame)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                fixed_width = 640
                fixed_height = 480
                frame_resized = cv2.resize(frame_rgb, (fixed_width, fixed_height))
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                time.sleep(0.05)  # ~20 FPS
            
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp nhận diện: {e}")
                time.sleep(0.1)
    # Xử lý các biển số đã được phát hiện
    def process_detected_plates(self, plates):
        try:
            plate = plates[0]
            plate_text = plate['text']
            if len(plate_text) >= 5:
                if plate_text != self.last_detected_plate:
                    self.last_detection_time = time.time()
                    self.last_detected_plate = plate_text
                    is_exit = self.db_manager.is_plate_in_database(plate_text)
                    self.db_manager.save_to_database(plate_text, exit=is_exit)
                    status_text = f"Xe ra: {plate_text}" if is_exit else f"Xe vào: {plate_text}"
                    status_color = "#F44336" if is_exit else "#4CAF50"
                    self.after(0, lambda: self.update_result(plate_text, status_text, status_color))
                    self.add_log_message(f"Đã nhận diện biển số: {plate_text} - {status_text}")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý biển số đã phát hiện: {e}")
        finally:
            self.processing = False
    
    # Xử lý frame để nhận diện biển số
    def process_frame(self, frame):
        try:
            plates = self.plate_detector.detect_license_plates(frame)
            if plates:
                plate = plates[0]
                plate_text = plate['text']
                if len(plate_text) >= 5:  
                    if plate_text != self.last_detected_plate:
                        self.last_detection_time = time.time()
                        self.last_detected_plate = plate_text
                        is_exit = self.db_manager.is_plate_in_database(plate_text)
                        self.db_manager.save_to_database(plate_text, exit=is_exit)
                        status_text = f"Xe ra: {plate_text}" if is_exit else f"Xe vào: {plate_text}"
                        status_color = "#F44336" if is_exit else "#4CAF50"
                        self.after(0, lambda: self.update_result(plate_text, status_text, status_color))
                        self.add_log_message(f"Đã nhận diện biển số: {plate_text} - {status_text}")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý frame: {e}")
        finally:
            self.processing = False
    
    # Cập nhật kết quả lên UI
    def update_result(self, plate_text, status_text, status_color):
        self.result_value.configure(text=plate_text)
        self.inout_value.configure(text=status_text.split(": ")[0], text_color=status_color)
    
    # Thêm thông tin trạng thái vào frame
    def add_status_to_frame(self, frame):
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        status_frame = frame.copy()
        camera_status = self.camera.get_status()
        cv2.putText(status_frame, f"FPS: {camera_status['fps']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        status_text = "Connected" if camera_status['connected'] else "Disconnected"
        status_color = (0, 255, 0) if camera_status['connected'] else (0, 0, 255)
        cv2.putText(status_frame, f"Status: {status_text}",(10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        cooldown_remaining = max(0, self.cooldown_time - (time.time() - self.last_detection_time))
        if cooldown_remaining > 0:
            cv2.putText(status_frame, f"Cooldown: {cooldown_remaining:.1f}s", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        return status_frame
    
    # Hàm để dừng camera và giải phóng tài nguyên
    def reconnect_camera(self):
        self.camera.stop()
        if self.camera.connect():
            self.camera.start()
            self.add_log_message("Đã kết nối lại camera thành công.")
        else:
            self.add_log_message("Không thể kết nối lại camera!")
    
    
    # Thêm tin nhắn vào log
    def add_log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")  # Cuộn xuống dưới
        self.log_text.configure(state="disabled")