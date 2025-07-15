import cv2

# ---------------- CẤU HÌNH RTSP CAMERA IMOU ---------------- #
# Hãy thay đổi các thông tin sau cho đúng với camera của bạn
USERNAME = "admin"               # Tên đăng nhập vào camera
PASSWORD = "L250C321"             # Mật khẩu đăng nhập
IP_ADDRESS = "192.168.142.201"     # Địa chỉ IP của camera (có thể kiểm tra trong app IMOU)

# Tạo URL RTSP
rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{IP_ADDRESS}:554/cam/realmonitor?channel=1&subtype=1"

# ----------------------------------------------------------- #
print(f"🟡 Đang kết nối tới camera tại: {rtsp_url}")
cap = cv2.VideoCapture(rtsp_url)

# Kiểm tra kết nối
if not cap.isOpened():
    print("❌ Không thể kết nối tới camera. Vui lòng kiểm tra:")
    print("- Địa chỉ IP đúng chưa?")
    print("- Tài khoản & mật khẩu đúng chưa?")
    print("- Camera & máy tính có cùng mạng Wi-Fi không?")
    exit()

print("✅ Kết nối thành công. Đang phát video...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Không nhận được khung hình. Đang chờ lại...")
        continue

    # Hiển thị video
    cv2.imshow("Camera IMOU", frame)

    # Bấm phím 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("🛑 Đã dừng.")
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()
