import re
import cv2
import torch
import logging
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
from ppocr.utils.logging import get_logger as ppocr_get_logger

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
        try:
            self.yolo_model = torch.hub.load(MODEL_PATHS['yolov5_path'],
                                            'custom',
                                            path=MODEL_PATHS['license_plate_model'],
                                            force_reload=True,
                                            source='local').to(self.device).eval()
            logger.info("Đã tải mô hình YOLOv5 thành công")
        except Exception as e:
            logger.error(f"Lỗi tải mô hình YOLOv5: {e}")
            self.yolo_model = None
        try:
            self.text_detector = PaddleOCR(
                ocr_version="PP-OCRv3",
                det_model_dir=MODEL_PATHS['paddle_det_model'],
                use_angle_cls=False,rec_model_dir=None,cls_model_dir=None,
                lang="en",use_gpu=False,show_log=False)
            logger.info("Đã tải mô hình PaddleOCR thành công")
        except Exception as e:
            logger.error(f"Lỗi tải mô hình PaddleOCR: {e}")
            self.text_detector = None
    
    def normalize_license_plate(self, raw_text):
        if not raw_text or raw_text.strip() == "":
            return ""
        clean_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        match = re.match(r'^(\d{2})([A-Z]{1,2})(.+)$', clean_text)
        if match:
            area_code = match.group(1)      
            letter_code = match.group(2)    
            remaining = match.group(3)      
            if len(letter_code) == 1 and remaining and remaining[0] in '123456789':
                letter_code += remaining[0] 
                number_code = remaining[1:]  
            else:
                number_code = remaining     
            return f"{area_code}-{letter_code} {number_code}"
        return clean_text
    
    def run(self, img):
        ocr_result = ' '
        try:
            results = self.text_detector.ocr(img, rec=True)
            if results[0] is not None:
                texts = []
                for line in results[0]:
                    texts.append(line[1][0])
                combined_text = ''.join(texts)
                normalized = self.normalize_license_plate(combined_text)
                ocr_result = normalized if normalized else combined_text
        except Exception as e:
            logger.error(f"Lỗi OCR: {e}")
            pass
        return ocr_result
    
    def detect_license_plates(self, frame):
        if self.yolo_model is None:
            return []
        try:
            plates = self.yolo_model(frame, size=640)
            list_plates = plates.pandas().xyxy[0].values.tolist()
            detected_plates = []
            
            for plate in list_plates:
                x = int(plate[0])  # xmin
                y = int(plate[1])  # ymin
                w = int(plate[2] - plate[0])  # xmax - xmin
                h = int(plate[3] - plate[1])  # ymax - ymin  
                crop_img = frame[y:y+h, x:x+w]
                
                results = self.run(crop_img)
                if results == " ":
                    text = " "
                else:
                    text = results
                
                detected_plates.append({
                    'text': text,
                    'box': (int(plate[0]), int(plate[1]), int(plate[2]), int(plate[3])),
                    'confidence': plate[4]
                })
            
            return detected_plates
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện biển số: {e}")
            return []
    
    def annotate_frame(self, frame, plates):
        annotated_frame = frame.copy()
        for plate in plates:
            x1, y1, x2, y2 = plate['box']
            text = plate['text']
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color=(0, 0, 225), thickness=2)
            cv2.putText(annotated_frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
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