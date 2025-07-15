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
        
        # Database and camera setup
        self.db_manager = DatabaseManager()
        camera_manager = get_camera_manager()
        self.camera = camera_manager.get_camera('license_plate')
        self.plate_detector = LicensePlateDetector()
        
        # Threading control
        self.running = False
        self.detection_thread = None
        self.display_thread = None
        self.stop_flag = threading.Event()
        
        # Detection parameters
        self.detection_interval = 2.0  # Process detection every 2 seconds
        self.cooldown_time = 15.0  # 15 seconds between same plate detections
        self.last_detection_time = 0
        self.last_detected_plate = None
        self.detection_lock = threading.Lock()
        
        # Frame management
        self.current_frame = None
        self.annotated_frame = None
        self.frame_lock = threading.Lock()
        self.last_frame_update = 0
        self.display_fps = 15  # Limit display to 15 FPS
        
        # Detection results
        self.current_detections = []
        self.detection_confidence_threshold = 0.7
        
        self.setup_ui()
        logger.info("Đã khởi tạo trang quản lý xe vào/ra")
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self, 
            text="Quản lý xe vào/ra",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Video frame
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.video_frame.grid_propagate(False)
        
        self.video_label = tk.Label(self.video_frame, bg="#1a1a1a")
        self.video_label.pack(expand=True, fill="both")
        
        # Results frame
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Detection result
        self.result_label_frame = ctk.CTkFrame(self.result_frame)
        self.result_label_frame.pack(fill="x", padx=20, pady=10)
        
        self.result_title = ctk.CTkLabel(
            self.result_label_frame,
            text="Kết quả nhận diện biển số:",
            font=ctk.CTkFont(size=16)
        )
        self.result_title.pack(side="left", padx=10)
        
        self.result_value = ctk.CTkLabel(
            self.result_label_frame,
            text="---",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4CAF50"
        )
        self.result_value.pack(side="left", padx=10)
        
        # In/Out status
        self.inout_frame = ctk.CTkFrame(self.result_frame)
        self.inout_frame.pack(fill="x", padx=20, pady=10)
        
        self.inout_title = ctk.CTkLabel(
            self.inout_frame,
            text="Trạng thái:",
            font=ctk.CTkFont(size=16)
        )
        self.inout_title.pack(side="left", padx=10)
        
        self.inout_value = ctk.CTkLabel(
            self.inout_frame,
            text="---",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2196F3"
        )
        self.inout_value.pack(side="left", padx=10)
        
        # Detection confidence
        self.confidence_frame = ctk.CTkFrame(self.result_frame)
        self.confidence_frame.pack(fill="x", padx=20, pady=10)
        
        self.confidence_title = ctk.CTkLabel(
            self.confidence_frame,
            text="Độ tin cậy:",
            font=ctk.CTkFont(size=16)
        )
        self.confidence_title.pack(side="left", padx=10)
        
        self.confidence_value = ctk.CTkLabel(
            self.confidence_frame,
            text="---",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FF9800"
        )
        self.confidence_value.pack(side="left", padx=10)
        
        # Activity log
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.log_title = ctk.CTkLabel(
            self.log_frame,
            text="Log hoạt động",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.log_title.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            height=100,
            font=ctk.CTkFont(size=12)
        )
        self.log_text.pack(fill="x", padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")
    
    def on_enter(self):
        """Called when page is displayed"""
        self.stop_flag.clear()
        self.running = True
        
        # Configure video frame
        self.video_frame.configure(height=480, width=640)
        self.video_label.configure(width=640, height=480)
        
        # Start threads
        self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.display_thread = threading.Thread(target=self.display_loop, daemon=True)
        
        self.detection_thread.start()
        self.display_thread.start()
        
        self.add_log_message("Đã khởi động hệ thống nhận diện biển số.")
        logger.info("Đã vào trang quản lý xe vào/ra")
    
    def on_leave(self):
        """Called when leaving page"""
        self.running = False
        self.stop_flag.set()
        
        # Wait for threads to finish
        if self.detection_thread:
            self.detection_thread.join(timeout=2.0)
            self.detection_thread = None
            
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
            self.display_thread = None
        
        self.add_log_message("Đã dừng hệ thống nhận diện biển số.")
        logger.info("Đã rời khỏi trang quản lý xe vào/ra")
    
    def detection_loop(self):
        """Separate thread for license plate detection"""
        last_detection_run = 0
        
        while self.running and not self.stop_flag.is_set():
            try:
                current_time = time.time()
                
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is None or frame.size == 0:
                    time.sleep(0.1)
                    continue
                
                # Crop frame to focus on license plate area
                height, width = frame.shape[:2]
                cropped_frame = frame[height//2:height, :]  # Bottom half
                cropped_frame = cropped_frame[60:, :]  # Remove top 60 pixels
                
                # Update current frame for display
                with self.frame_lock:
                    self.current_frame = cropped_frame.copy()
                
                # Run detection at intervals
                if current_time - last_detection_run >= self.detection_interval:
                    last_detection_run = current_time
                    
                    # Detect license plates
                    detections = self.plate_detector.detect_license_plates(cropped_frame)
                    
                    # Process valid detections
                    if detections:
                        best_detection = self.get_best_detection(detections)
                        if best_detection:
                            self.process_detection(best_detection)
                    
                    # Update detections for display
                    with self.detection_lock:
                        self.current_detections = detections
                
                time.sleep(0.1)  # Small delay to prevent CPU overuse
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp nhận diện: {e}")
                time.sleep(0.01)
    
    def display_loop(self):
        """Separate thread for video display"""
        while self.running and not self.stop_flag.is_set():
            try:
                current_time = time.time()
                
                # Limit display FPS
                if current_time - self.last_frame_update < (1.0 / self.display_fps):
                    time.sleep(0.01)
                    continue
                
                self.last_frame_update = current_time
                
                # Get current frame
                with self.frame_lock:
                    if self.current_frame is None:
                        time.sleep(0.05)
                        continue
                    display_frame = self.current_frame.copy()
                
                # Get current detections
                with self.detection_lock:
                    detections = self.current_detections.copy()
                
                # Annotate frame
                if detections:
                    display_frame = self.plate_detector.annotate_frame(display_frame, detections)
                
                # Add status information
                display_frame = self.add_status_to_frame(display_frame)
                
                # Convert and display
                self.update_display(display_frame)
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp hiển thị: {e}")
                time.sleep(0.1)
    
    def get_best_detection(self, detections):
        """Select the best detection based on confidence and consensus"""
        if not detections:
            return None
        
        # Filter by confidence and consensus
        valid_detections = []
        for detection in detections:
            if (detection['confidence'] >= self.detection_confidence_threshold and
                detection.get('has_consensus', False) and
                detection['text'] and len(detection['text']) >= 5):
                valid_detections.append(detection)
        
        if not valid_detections:
            # Fallback to high confidence detections without consensus
            for detection in detections:
                if (detection['confidence'] >= 0.8 and
                    detection['text'] and len(detection['text']) >= 5):
                    valid_detections.append(detection)
        
        if valid_detections:
            # Return highest confidence detection
            return max(valid_detections, key=lambda x: x['confidence'])
        
        return None
    
    def process_detection(self, detection):
        """Process a valid license plate detection"""
        try:
            plate_text = detection['text']
            confidence = detection['confidence']
            
            current_time = time.time()
            
            # Check cooldown period
            if (plate_text == self.last_detected_plate and 
                current_time - self.last_detection_time < self.cooldown_time):
                return
            
            # Update detection tracking
            self.last_detection_time = current_time
            self.last_detected_plate = plate_text
            
            # Determine entry or exit
            is_exit = self.db_manager.is_plate_in_database(plate_text)
            
            # Save to database
            success = self.db_manager.save_to_database(plate_text, exit=is_exit)
            
            if success:
                # Update UI
                status_text = "Xe ra" if is_exit else "Xe vào"
                status_color = "#F44336" if is_exit else "#4CAF50"
                
                self.after(0, lambda: self.update_result_ui(
                    plate_text, status_text, status_color, confidence
                ))
                
                # Log activity
                log_message = f"Đã nhận diện: {plate_text} - {status_text} (Độ tin cậy: {confidence:.2f})"
                self.add_log_message(log_message)
                
                logger.info(f"Processed detection: {plate_text} - {status_text}")
            else:
                self.add_log_message(f"Lỗi lưu dữ liệu cho biển số: {plate_text}")
                
        except Exception as e:
            logger.error(f"Lỗi khi xử lý nhận diện: {e}")
    
    def update_result_ui(self, plate_text, status_text, status_color, confidence):
        """Update the UI with detection results"""
        self.result_value.configure(text=plate_text)
        self.inout_value.configure(text=status_text, text_color=status_color)
        self.confidence_value.configure(text=f"{confidence:.2f}")
    
    def update_display(self, frame):
        """Update the video display"""
        try:
            if frame is None or frame.size == 0:
                return
            
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fixed dimensions
            fixed_width = 640
            fixed_height = 480
            frame_resized = cv2.resize(frame_rgb, (fixed_width, fixed_height))
            
            # Convert to PhotoImage
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update label
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        except Exception as e:
            logger.error(f"Lỗi cập nhật hiển thị: {e}")
    
    def add_status_to_frame(self, frame):
        """Add status information to frame"""
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        status_frame = frame.copy()
        
        # Camera status
        camera_status = self.camera.get_status()
        
        # FPS
        cv2.putText(status_frame, f"FPS: {camera_status['fps']}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Connection status
        status_text = "Connected" if camera_status['connected'] else "Disconnected"
        status_color = (0, 255, 0) if camera_status['connected'] else (0, 0, 255)
        cv2.putText(status_frame, f"Status: {status_text}",
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        
        # Cooldown timer
        cooldown_remaining = max(0, self.cooldown_time - (time.time() - self.last_detection_time))
        if cooldown_remaining > 0:
            cv2.putText(status_frame, f"Cooldown: {cooldown_remaining:.1f}s", 
                       (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        
        # Detection count
        detection_count = len(self.current_detections)
        cv2.putText(status_frame, f"Detections: {detection_count}", 
                   (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        
        return status_frame
    
    def add_log_message(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        def update_log():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", formatted_message)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        
        if threading.current_thread() == threading.main_thread():
            update_log()
        else:
            self.after(0, update_log)