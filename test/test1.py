import cv2
import time

USERNAME = "admin"
PASSWORD = "admin123"
IP_ADDRESS = "192.168.137.38"
rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{IP_ADDRESS}:554/onvif1" # Địa chỉ RTSP của camera YOOSEE

print(f"🟡 Đang kết nối tới camera tại: {rtsp_url}")
cap = cv2.VideoCapture(rtsp_url)

# Kiểm tra kết nối
retry = 0
while not cap.isOpened() and retry < 1:
    print("⏳ Đang thử lại kết nối...")
    time.sleep(2)
    cap.open(rtsp_url)
    retry += 1

if not cap.isOpened():
    print("❌ Không thể kết nối tới camera.")
    exit()

print("✅ Kết nối thành công. Đang phát video...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Không nhận được khung hình. Đang chờ lại...")
        time.sleep(0.5)
        continue

    cv2.imshow("Camera YOOSEE", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("🛑 Đã dừng.")
        break
import cv2
print(cv2.getBuildInformation())


cap.release()
cv2.destroyAllWindows()
