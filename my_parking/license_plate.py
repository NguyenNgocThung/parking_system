import re
import cv2
import torch
import logging
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
from ppocr.utils.logging import get_logger as ppocr_get_logger
import time
from collections import Counter

# Cấu hình từ config
from config import MODEL_PATHS, LICENSE_PLATE_CAMERA

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LicensePlateDetector:
    def __init__(self):
        ppocr_get_logger().setLevel(logging.ERROR)
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        logger.info(f"Sử dụng thiết bị: {self.device}")
        
        # Detection parameters
        self.min_confidence = 0.2
        self.min_plate_width = 80
        self.min_plate_height = 25
        self.detection_history = []
        self.history_size = 5
        self.consensus_threshold = 3
        
        try:
            self.yolo_model = torch.hub.load(MODEL_PATHS['yolov5_path'],
                                            'custom',
                                            path=MODEL_PATHS['license_plate_model'],
                                            force_reload=True,
                                            source='local').to(self.device).eval()
            # Optimize model
            self.yolo_model.conf = self.min_confidence
            self.yolo_model.iou = 0.45
            logger.info("Đã tải mô hình YOLOv5 thành công")
        except Exception as e:
            logger.error(f"Lỗi tải mô hình YOLOv5: {e}")
            self.yolo_model = None
            
        try:
            self.text_detector = PaddleOCR(
                ocr_version="PP-OCRv3",
                det_model_dir=MODEL_PATHS['paddle_det_model'],
                use_angle_cls=False,
                rec_model_dir=None,
                cls_model_dir=None,
                lang="en",
                use_gpu=torch.cuda.is_available(),
                show_log=False,
                det_limit_side_len=960,
                det_limit_type='max'
            )
            logger.info("Đã tải mô hình PaddleOCR thành công")
        except Exception as e:
            logger.error(f"Lỗi tải mô hình PaddleOCR: {e}")
            self.text_detector = None
    
    def normalize_license_plate(self, raw_text):
        if not raw_text or raw_text.strip() == "":
            return ""
        
        # Clean and uppercase
        clean_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        
        # Minimum length check
        if len(clean_text) < 5:
            return ""
        
        # Vietnamese license plate pattern
        match = re.match(r'^(\d{2})([A-Z]{1,2})(.+)$', clean_text)
        if match:
            area_code = match.group(1)
            letter_code = match.group(2)
            remaining = match.group(3)
            
            # Handle single letter followed by digit
            if len(letter_code) == 1 and remaining and remaining[0] in '123456789':
                letter_code += remaining[0]
                number_code = remaining[1:]
            else:
                number_code = remaining
            
            # Validate number part
            if len(number_code) >= 3:
                return f"{area_code}-{letter_code} {number_code}"
        
        return clean_text if len(clean_text) >= 5 else ""
    
    def preprocess_plate_image(self, img):
        """Preprocess plate image for better OCR"""
        try:
            # Resize if too small
            h, w = img.shape[:2]
            if w < 120 or h < 40:
                scale = max(120/w, 40/h)
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            
            # Convert to grayscale for processing
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply CLAHE for contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Convert back to BGR for PaddleOCR
            processed = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            return processed
        except Exception as e:
            logger.error(f"Lỗi tiền xử lý ảnh: {e}")
            return img
    
    def run_ocr_with_validation(self, img):
        """Run OCR with multiple attempts and validation"""
        ocr_result = ""
        
        try:
            # Original image
            results = self.text_detector.ocr(img, rec=True)
            if results[0] is not None:
                texts = []
                for line in results[0]:
                    if len(line) >= 2 and line[1][1] > 0.7:  # Confidence threshold
                        texts.append(line[1][0])
                
                if texts:
                    combined_text = ''.join(texts)
                    normalized = self.normalize_license_plate(combined_text)
                    if normalized:
                        ocr_result = normalized
            
            # If no good result, try preprocessed image
            if not ocr_result:
                processed_img = self.preprocess_plate_image(img)
                results = self.text_detector.ocr(processed_img, rec=True)
                if results[0] is not None:
                    texts = []
                    for line in results[0]:
                        if len(line) >= 2 and line[1][1] > 0.6:  # Lower threshold for processed
                            texts.append(line[1][0])
                    
                    if texts:
                        combined_text = ''.join(texts)
                        normalized = self.normalize_license_plate(combined_text)
                        if normalized:
                            ocr_result = normalized
                            
        except Exception as e:
            logger.error(f"Lỗi OCR: {e}")
        
        return ocr_result
    
    def validate_detection_consensus(self, new_text):
        """Use detection history for consensus validation"""
        if not new_text or len(new_text) < 5:
            return None
        
        # Add to history
        self.detection_history.append(new_text)
        if len(self.detection_history) > self.history_size:
            self.detection_history.pop(0)
        
        # Count occurrences
        if len(self.detection_history) >= self.consensus_threshold:
            counter = Counter(self.detection_history)
            most_common = counter.most_common(1)[0]
            
            # If we have consensus
            if most_common[1] >= self.consensus_threshold:
                return most_common[0]
        
        return None
    
    def detect_license_plates(self, frame):
        if self.yolo_model is None:
            return []
        
        try:
            start_time = time.time()
            
            # Run YOLO detection
            results = self.yolo_model(frame, size=640)
            detections = results.pandas().xyxy[0].values.tolist()
            
            detected_plates = []
            
            for detection in detections:
                confidence = detection[4]
                if confidence < self.min_confidence:
                    continue
                
                x1, y1, x2, y2 = map(int, detection[:4])
                width = x2 - x1
                height = y2 - y1
                
                # Size validation
                if width < self.min_plate_width or height < self.min_plate_height:
                    continue
                
                # Aspect ratio validation (license plates are typically wider)
                aspect_ratio = width / height
                if not (1.5 <= aspect_ratio <= 6.0):
                    continue
                
                # Extract plate region with padding
                pad = 5
                y1_crop = max(0, y1 - pad)
                y2_crop = min(frame.shape[0], y2 + pad)
                x1_crop = max(0, x1 - pad)
                x2_crop = min(frame.shape[1], x2 + pad)
                
                crop_img = frame[y1_crop:y2_crop, x1_crop:x2_crop]
                
                if crop_img.size == 0:
                    continue
                
                # OCR with validation
                text = self.run_ocr_with_validation(crop_img)
                
                # Use consensus validation
                consensus_text = self.validate_detection_consensus(text)
                
                detected_plates.append({
                    'text': consensus_text if consensus_text else text,
                    'raw_text': text,
                    'box': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'has_consensus': consensus_text is not None
                })
            
            # Sort by confidence and return best results
            detected_plates.sort(key=lambda x: x['confidence'], reverse=True)
            
            processing_time = time.time() - start_time
            if processing_time > 0.5:  # Log slow detections
                logger.warning(f"Phát hiện chậm: {processing_time:.2f}s")
            
            return detected_plates[:3]  # Return top 3 detections
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện biển số: {e}")
            return []
    
    def annotate_frame(self, frame, plates):
        annotated_frame = frame.copy()
        
        for plate in plates:
            x1, y1, x2, y2 = plate['box']
            text = plate['text'] if plate['text'] else "Detecting..."
            confidence = plate['confidence']
            has_consensus = plate.get('has_consensus', False)
            
            # Color based on consensus
            color = (0, 255, 0) if has_consensus else (0, 165, 255)
            thickness = 3 if has_consensus else 2
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw text with background
            font_scale = 0.8
            font_thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
            )
            
            # Background rectangle
            cv2.rectangle(annotated_frame, 
                         (x1, y1 - text_height - 10), 
                         (x1 + text_width, y1), 
                         color, -1)
            
            # Text
            cv2.putText(annotated_frame, text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), font_thickness)
            
            # Confidence indicator
            conf_text = f"{confidence:.2f}"
            cv2.putText(annotated_frame, conf_text, (x2 - 60, y2 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return annotated_frame

# Kết nối đến camera
def connect_to_camera():
    rtsp_url = LICENSE_PLATE_CAMERA['url']
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        logger.error(f"Không thể kết nối đến camera: {rtsp_url}")
        return None
    logger.info("Đã kết nối thành công đến camera nhận diện biển số")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap